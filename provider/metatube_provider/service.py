"""Provider application service."""

from __future__ import annotations

from typing import Any

from .api_client import APIClient, APIError
from .config import Settings
from .mapper import MetadataMapper
from .plex import image_container, media_container, provider_response
from .provider_id import MergedProviderID, ProviderID, ProviderRef, decode_rating_key, parse_guid
from .utils import has_chinese_subtitle, parse_filename_without_ext, parse_list


class ProviderService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.api = APIClient(
            server=settings.api_server,
            token=settings.api_token,
            timeout=settings.request_timeout,
        )
        self.mapper = MetadataMapper(settings, self.api)

    def provider(self) -> dict[str, Any]:
        return provider_response(
            self.settings.provider_identifier,
            self.settings.provider_title,
            self.settings.path_prefix,
        )

    def match(self, body: dict[str, Any], language: str | None = None) -> dict[str, Any]:
        if int(body.get("type") or 0) != 1:
            return media_container(self.settings.provider_identifier, [])

        badge = has_chinese_subtitle(str(body.get("filename") or ""))
        pid = self.pid_from_match(body)
        if pid:
            movie = self.movie_info_for_pid(pid)
            rating_pid = self.with_badge(pid, badge)
            return media_container(
                self.settings.provider_identifier,
                [self.mapper.movie_to_metadata(movie, rating_pid, language)],
            )

        query = self.query_from_match(body)
        if not query:
            return media_container(self.settings.provider_identifier, [])

        movies = self.api.search_movie(q=query)
        movies = self.filter_movies(movies, query=query)

        manual = int(body.get("manual") or 0) == 1
        metadata = self.match_metadata(movies, query=query, badge=badge, manual=manual)
        return media_container(self.settings.provider_identifier, metadata)

    def metadata(self, rating_key: str, language: str | None = None) -> dict[str, Any]:
        pid = decode_rating_key(rating_key)
        movie = self.movie_info_for_pid(pid)
        return media_container(self.settings.provider_identifier, [self.mapper.movie_to_metadata(movie, pid, language)])

    def images(self, rating_key: str) -> dict[str, Any]:
        pid = decode_rating_key(rating_key)
        image_pid = primary_source(pid)
        movie = self.api.get_movie_info(image_pid.provider, image_pid.id, lazy=True)
        title = movie.get("title") or movie.get("number") or image_pid.id
        badge = self.settings.badge_url if pid.badge and self.settings.enable_badges else None
        images = [
            {
                "type": "coverPoster",
                "url": self.api.primary_image_url(image_pid.provider, image_pid.id, pos=image_pid.position, badge=badge),
                "alt": title,
            },
            {
                "type": "background",
                "url": self.api.backdrop_image_url(image_pid.provider, image_pid.id),
                "alt": title,
            },
        ]
        return image_container(self.settings.provider_identifier, images)

    def match_metadata(
        self,
        movies: list[dict[str, Any]],
        query: str | None,
        badge: bool,
        manual: bool,
    ) -> list[dict[str, Any]]:
        if not movies:
            return []

        metadata: list[dict[str, Any]] = []
        if should_merge_matches(movies, query):
            metadata.append(self.mapper.merged_search_result_to_metadata(movies, badge=badge))
            if not manual:
                return metadata

        metadata.extend(self.mapper.search_result_to_metadata(movie, badge=badge) for movie in movies)
        limit = self.settings.manual_limit if manual else 1
        return metadata[:limit]

    def movie_info_for_pid(self, pid: ProviderRef) -> dict[str, Any]:
        if isinstance(pid, MergedProviderID):
            movies = []
            for source in pid.sources:
                try:
                    movies.append(self.api.get_movie_info(source.provider, source.id, lazy=(source.update is not True)))
                except APIError:
                    continue
            if not movies:
                raise APIError("all MetaTube merge sources failed")
            return merge_movie_details(movies)

        return self.api.get_movie_info(pid.provider, pid.id, lazy=(pid.update is not True))

    @staticmethod
    def with_badge(pid: ProviderRef, badge: bool) -> ProviderRef:
        if isinstance(pid, MergedProviderID):
            return MergedProviderID(sources=pid.sources, badge=badge)
        return ProviderID(pid.provider, pid.id, pid.position, pid.update, badge)

    def pid_from_match(self, body: dict[str, Any]) -> ProviderRef | None:
        guid = body.get("guid")
        if isinstance(guid, str):
            pid = parse_guid(guid, self.settings.provider_identifier)
            if pid:
                return pid

        title = body.get("title")
        if isinstance(title, str):
            return ProviderID.try_parse_legacy(title)

        return None

    def query_from_match(self, body: dict[str, Any]) -> str | None:
        if not int(body.get("manual") or 0) and body.get("filename"):
            return parse_filename_without_ext(str(body["filename"]))
        if body.get("title"):
            return str(body["title"])
        if body.get("filename"):
            return parse_filename_without_ext(str(body["filename"]))
        return None

    def filter_movies(self, movies: list[dict[str, Any]], query: str | None = None) -> list[dict[str, Any]]:
        if not self.settings.enable_movie_provider_filter:
            filtered = list(movies)
        else:
            providers = parse_list(self.settings.movie_provider_filter)
            if not providers:
                filtered = list(movies)
            else:
                filtered = [movie for movie in movies if str(movie.get("provider", "")).upper() in providers]
                filtered.sort(key=lambda movie: providers.index(str(movie.get("provider", "")).upper()))

        exact = exact_catalog_matches(filtered, query)
        if exact:
            return exact
        return filtered


def exact_catalog_matches(movies: list[dict[str, Any]], query: str | None) -> list[dict[str, Any]]:
    needle = normalize_catalog_number(query)
    if not is_catalog_number(needle):
        return []

    return unique_movies([
        movie for movie in movies
        if needle in {
            normalize_catalog_number(movie.get("number")),
            normalize_catalog_number(movie.get("id")),
        }
    ])


def normalize_catalog_number(value: Any) -> str:
    return "".join(char for char in str(value or "").upper() if char.isalnum())


def is_catalog_number(value: str) -> bool:
    return len(value) >= 4 and any(char.isalpha() for char in value) and any(char.isdigit() for char in value)


def should_merge_matches(movies: list[dict[str, Any]], query: str | None) -> bool:
    return len(exact_catalog_matches(movies, query)) > 1


def merge_movie_details(movies: list[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(movies[0])

    for field in (
        "title",
        "number",
        "homepage",
        "cover_url",
        "thumb_url",
        "big_cover_url",
        "big_thumb_url",
        "summary",
        "director",
        "maker",
        "label",
        "series",
        "release_date",
        "preview_video_url",
        "preview_video_hls_url",
    ):
        if not has_value(merged.get(field)):
            value = first_value(movies, field)
            if has_value(value):
                merged[field] = value

    for field in ("runtime", "score"):
        if not positive_number(merged.get(field)):
            value = first_positive_number(movies, field)
            if value is not None:
                merged[field] = value

    for field in ("actors", "genres", "preview_images"):
        merged[field] = unique_values(movie.get(field) for movie in movies)

    merged["sources"] = [
        {"provider": movie.get("provider"), "id": movie.get("id")}
        for movie in movies
        if movie.get("provider") and movie.get("id")
    ]
    return merged


def primary_source(pid: ProviderRef) -> ProviderID:
    return pid.primary if isinstance(pid, MergedProviderID) else pid


def first_value(movies: list[dict[str, Any]], field: str) -> Any:
    for movie in movies:
        value = movie.get(field)
        if has_value(value):
            return value
    return None


def first_positive_number(movies: list[dict[str, Any]], field: str) -> Any:
    for movie in movies:
        value = movie.get(field)
        if positive_number(value):
            return value
    return None


def has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return True


def positive_number(value: Any) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def unique_values(groups: Any) -> list[Any]:
    values: list[Any] = []
    seen: set[str] = set()
    for group in groups:
        if not isinstance(group, list):
            continue
        for item in group:
            marker = str(item)
            if not marker or marker in seen:
                continue
            seen.add(marker)
            values.append(item)
    return values


def unique_movies(movies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for movie in movies:
        key = (str(movie.get("provider") or ""), str(movie.get("id") or ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(movie)
    return unique
