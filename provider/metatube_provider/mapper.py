"""Map MetaTube API objects to Plex metadata JSON."""

from __future__ import annotations

import time
from typing import Any

from .api_client import APIClient
from .config import Settings, TRANSLATION_SUMMARY, TRANSLATION_TITLE
from .provider_id import MergedProviderID, ProviderID, ProviderRef, encode_rating_key
from .plex import METADATA_PATH, prefixed_path
from .utils import (
    DEFAULT_CONTENT_RATING,
    DEFAULT_COUNTRY,
    DEFAULT_TITLE_TEMPLATE,
    date_string,
    parse_list,
    parse_table,
    table_substitute,
    year,
)


AV_BASE = "AvBase"
AV_BASE_SUPPORTED_PROVIDERS = {"DUGA", "FANZA", "GETCHU", "MGS", "PCOLLE"}
G_FRIENDS = "Gfriends"


class MetadataMapper:
    def __init__(self, settings: Settings, api: APIClient):
        self.settings = settings
        self.api = api

    def search_result_to_metadata(self, movie: dict[str, Any], badge: bool = False) -> dict[str, Any]:
        pid = movie_provider_id(movie, badge=badge)
        rating_key = encode_rating_key(pid)
        release_date = str(movie.get("release_date") or "")
        thumb = self.api.primary_image_url(
            pid.provider,
            pid.id,
            url=movie.get("thumb_url"),
            pos=1.0,
            auto=True,
            badge=self.settings.badge_url if badge and self.settings.enable_badges else None,
        )

        return {
            "ratingKey": rating_key,
            "key": metadata_key(rating_key, self.settings.path_prefix),
            "guid": guid(self.settings.provider_identifier, rating_key),
            "type": "movie",
            "title": format_default_title(movie),
            "summary": format_default_title(movie),
            "originallyAvailableAt": date_string(release_date),
            "year": year(release_date),
            "thumb": thumb,
            "Image": [{"type": "coverPoster", "url": thumb, "alt": format_default_title(movie)}],
            "Guid": [{"id": f"metatube://{pid.provider}/{pid.id}"}],
        }

    def merged_search_result_to_metadata(self, movies: list[dict[str, Any]], badge: bool = False) -> dict[str, Any]:
        primary = movies[0]
        sources = tuple(movie_provider_id(movie) for movie in movies)
        pid = MergedProviderID(sources=sources, badge=badge)
        image_pid = pid.primary
        rating_key = encode_rating_key(pid)
        release_date = str(primary.get("release_date") or "")
        title = format_default_title(primary)
        thumb = self.api.primary_image_url(
            image_pid.provider,
            image_pid.id,
            url=primary.get("thumb_url"),
            pos=1.0,
            auto=True,
            badge=self.settings.badge_url if badge and self.settings.enable_badges else None,
        )

        return {
            "ratingKey": rating_key,
            "key": metadata_key(rating_key, self.settings.path_prefix),
            "guid": guid(self.settings.provider_identifier, rating_key),
            "type": "movie",
            "title": title,
            "summary": f"Merged from {', '.join(source.provider for source in sources)}",
            "originallyAvailableAt": date_string(release_date),
            "year": year(release_date),
            "thumb": thumb,
            "Image": [{"type": "coverPoster", "url": thumb, "alt": title}],
            "Guid": source_guids(pid),
        }

    def movie_to_metadata(self, movie: dict[str, Any], pid: ProviderRef, language: str | None = None) -> dict[str, Any]:
        movie = dict(movie)
        release_date = str(movie.get("release_date") or "")
        original_title = str(movie.get("title") or "")
        badge = self.settings.badge_url if pid.badge and self.settings.enable_badges else None
        image_pid = primary_source(pid)

        self.apply_preferences(movie, language)

        rating_key = encode_rating_key(pid)
        title = self.format_title(movie)
        thumb = self.api.primary_image_url(image_pid.provider, image_pid.id, pos=image_pid.position, badge=badge)
        art = self.api.backdrop_image_url(image_pid.provider, image_pid.id)

        metadata: dict[str, Any] = {
            "ratingKey": rating_key,
            "key": metadata_key(rating_key, self.settings.path_prefix),
            "guid": guid(self.settings.provider_identifier, rating_key),
            "type": "movie",
            "title": title,
            "originalTitle": original_title,
            "summary": movie.get("summary") or "",
            "tagline": pid.legacy(),
            "contentRating": DEFAULT_CONTENT_RATING,
            "originallyAvailableAt": date_string(release_date),
            "year": year(release_date),
            "thumb": thumb,
            "art": art,
            "Image": [
                {"type": "coverPoster", "url": thumb, "alt": title},
                {"type": "background", "url": art, "alt": title},
            ],
            "Guid": source_guids(pid),
            "Country": [{"tag": DEFAULT_COUNTRY}],
            "Genre": [{"tag": genre} for genre in unique(movie.get("genres") or [])],
        }

        runtime = to_int(movie.get("runtime"))
        if runtime > 0:
            metadata["duration"] = runtime * 60 * 1000

        maker = str(movie.get("maker") or "").strip()
        if maker:
            metadata["studio"] = maker
            metadata["Studio"] = [{"tag": maker}]

        director = str(movie.get("director") or "").strip()
        if self.settings.enable_directors and director:
            metadata["Director"] = [{"tag": director}]

        actors = unique(movie.get("actors") or [])
        if actors:
            metadata["Role"] = self.roles(actors)

        if self.settings.enable_ratings:
            score = to_float(movie.get("score"))
            if score > 0:
                metadata["Rating"] = [
                    {
                        "image": "metatube://image.rating",
                        "type": "audience",
                        "value": min(score * 2.0, 10.0),
                    },
                ]

        return drop_none(metadata)

    def roles(self, actors: list[str]) -> list[dict[str, Any]]:
        roles: list[dict[str, Any]] = []
        for index, actor in enumerate(actors):
            role = {"tag": actor, "order": index + 1}
            if self.settings.enable_actor_images:
                actor_image = self.actor_image_url(actor)
                if actor_image:
                    role["thumb"] = actor_image
            roles.append(role)
        return roles

    def actor_image_url(self, name: str) -> str | None:
        try:
            results = self.api.search_actor(q=name, provider=G_FRIENDS, fallback=False)
        except Exception:
            return None
        for actor in results:
            images = actor.get("images") or []
            if images:
                return self.api.primary_image_url(G_FRIENDS, name, url=images[0], ratio=1.0, auto=True)
        return None

    def apply_preferences(self, movie: dict[str, Any], language: str | None) -> None:
        if self.settings.enable_real_actor_names and str(movie.get("provider", "")).upper() in AV_BASE_SUPPORTED_PROVIDERS:
            try:
                results = self.api.search_movie(q=str(movie.get("id") or ""), provider=AV_BASE)
            except Exception:
                results = []
            if len(results) == 1 and results[0].get("actors"):
                movie["actors"] = results[0]["actors"]

        if self.settings.enable_title_substitution and self.settings.title_substitution_table:
            table = parse_table(self.settings.title_substitution_table, sep="\n", b64=True)
            title = str(movie.get("title") or "")
            for old, new in table.items():
                title = title.replace(old, new)
            movie["title"] = title

        if self.settings.enable_actor_substitution and self.settings.actor_substitution_table:
            table = parse_table(self.settings.actor_substitution_table, sep="\n", b64=True)
            movie["actors"] = table_substitute(table, movie.get("actors") or [])

        if self.settings.enable_genre_substitution and self.settings.genre_substitution_table:
            table = parse_table(self.settings.genre_substitution_table, sep="\n", b64=True)
            movie["genres"] = table_substitute(table, movie.get("genres") or [])

        if language:
            if self.settings.translation_has(TRANSLATION_TITLE) and movie.get("title"):
                movie["title"] = self.translate_text(str(movie["title"]), language)
            if self.settings.translation_has(TRANSLATION_SUMMARY) and movie.get("summary"):
                movie["summary"] = self.translate_text(str(movie["summary"]), language)

    def translate_text(self, text: str, language: str) -> str:
        if not text or language.lower().startswith("ja"):
            return text

        params = parse_table(self.settings.translation_engine_parameters, origin_key=True)
        forced_language = params.pop("to", None)
        target_language = forced_language or language

        # Keep the old plugin's conservative request rate for translation APIs.
        time.sleep(1.0)
        try:
            return self.api.translate(text, target_language, self.settings.translation_engine, **params)
        except Exception:
            return text

    def format_title(self, movie: dict[str, Any]) -> str:
        template = self.settings.title_template if self.settings.enable_title_template else DEFAULT_TITLE_TEMPLATE
        release_date = str(movie.get("release_date") or "")
        actors = movie.get("actors") or []
        context = {
            "provider": movie.get("provider") or "",
            "id": movie.get("id") or "",
            "number": movie.get("number") or "",
            "title": movie.get("title") or "",
            "series": movie.get("series") or "",
            "maker": movie.get("maker") or "",
            "label": movie.get("label") or "",
            "director": movie.get("director") or "",
            "actors": " ".join(actors),
            "first_actor": actors[0] if actors else "",
            "year": year(release_date) or "",
            "date": date_string(release_date),
        }
        try:
            return template.format(**context).strip()
        except Exception:
            return format_default_title(movie)


def guid(provider_identifier: str, rating_key: str) -> str:
    return f"{provider_identifier}://movie/{rating_key}"


def metadata_key(rating_key: str, path_prefix: str = "") -> str:
    return prefixed_path(path_prefix, f"{METADATA_PATH}/{rating_key}")


def format_default_title(movie: dict[str, Any]) -> str:
    return DEFAULT_TITLE_TEMPLATE.format(number=movie.get("number") or "", title=movie.get("title") or "").strip()


def movie_provider_id(movie: dict[str, Any], badge: bool = False) -> ProviderID:
    provider = str(movie.get("provider") or "").strip()
    id = str(movie.get("id") or "").strip()
    if not provider or not id:
        raise ValueError("movie result is missing provider or id")
    return ProviderID(provider=provider, id=id, badge=badge)


def primary_source(pid: ProviderRef) -> ProviderID:
    return pid.primary if isinstance(pid, MergedProviderID) else pid


def source_guids(pid: ProviderRef) -> list[dict[str, str]]:
    sources = pid.sources if isinstance(pid, MergedProviderID) else (pid,)
    return [{"id": f"metatube://{source.provider}/{source.id}"} for source in sources]


def unique(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def drop_none(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None and item != []}
