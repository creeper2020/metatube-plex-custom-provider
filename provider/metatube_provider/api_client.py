"""Client for the existing MetaTube backend API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable
from urllib import parse, request


class APIError(RuntimeError):
    """Raised when the MetaTube backend returns an error or invalid payload."""


@dataclass(frozen=True)
class APIClient:
    server: str
    token: str = ""
    timeout: float = 20.0
    user_agent: str = "MetaTubeProvider/0.1"

    MOVIE_INFO_API = "/v1/movies/{provider}/{id}"
    MOVIE_REVIEW_API = "/v1/reviews/{provider}/{id}"
    ACTOR_SEARCH_API = "/v1/actors/search"
    MOVIE_SEARCH_API = "/v1/movies/search"
    PRIMARY_IMAGE_API = "/v1/images/primary/{provider}/{id}"
    THUMB_IMAGE_API = "/v1/images/thumb/{provider}/{id}"
    BACKDROP_IMAGE_API = "/v1/images/backdrop/{provider}/{id}"
    TRANSLATE_API = "/v1/translate"

    def build_url(self, path: str, **params: Any) -> str:
        base = self.server.rstrip("/") + "/"
        url = parse.urljoin(base, path.lstrip("/"))
        query = {
            key: self._query_value(value)
            for key, value in params.items()
            if value is not None
        }
        if query:
            url = f"{url}?{parse.urlencode(query)}"
        return url

    def get_json(self, url: str, require_auth: bool = False) -> Any:
        headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if require_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = request.Request(url, headers=headers)
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except Exception as exc:  # pragma: no cover - exercised against real PMS/backend
            raise APIError(f"MetaTube request failed: {url}: {exc}") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise APIError(f"MetaTube response is not valid JSON: {url}") from exc

        if isinstance(payload, dict) and payload.get("error"):
            error = payload["error"]
            code = error.get("code", "unknown")
            message = error.get("message", "unknown error")
            raise APIError(f"MetaTube API error: {code}: {message}")

        if not isinstance(payload, dict) or "data" not in payload:
            raise APIError("MetaTube response does not contain a data field")

        return payload["data"]

    def search_movie(self, q: str, provider: str | None = None, fallback: bool | None = None) -> list[dict[str, Any]]:
        url = self.build_url(self.MOVIE_SEARCH_API, q=q, provider=provider, fallback=fallback)
        data = self.get_json(url, require_auth=True)
        return list(data or [])

    def get_movie_info(self, provider: str, id: str, lazy: bool | None = None) -> dict[str, Any]:
        url = self.build_url(self.MOVIE_INFO_API.format(provider=provider, id=parse.quote(id, safe="")), lazy=lazy)
        data = self.get_json(url, require_auth=True)
        if not isinstance(data, dict):
            raise APIError("MetaTube movie info response is not an object")
        return data

    def get_movie_reviews(
        self,
        provider: str,
        id: str,
        homepage: str | None = None,
        lazy: bool | None = None,
    ) -> list[dict[str, Any]]:
        url = self.build_url(
            self.MOVIE_REVIEW_API.format(provider=provider, id=parse.quote(id, safe="")),
            homepage=homepage,
            lazy=lazy,
        )
        data = self.get_json(url, require_auth=True)
        return list(data or [])

    def search_actor(
        self,
        q: str,
        provider: str | None = None,
        fallback: bool | None = None,
    ) -> list[dict[str, Any]]:
        url = self.build_url(self.ACTOR_SEARCH_API, q=q, provider=provider, fallback=fallback)
        data = self.get_json(url, require_auth=True)
        return list(data or [])

    def primary_image_url(self, provider: str, id: str, **params: Any) -> str:
        return self.build_url(self.PRIMARY_IMAGE_API.format(provider=provider, id=parse.quote(id, safe="")), **params)

    def thumb_image_url(self, provider: str, id: str, **params: Any) -> str:
        return self.build_url(self.THUMB_IMAGE_API.format(provider=provider, id=parse.quote(id, safe="")), **params)

    def backdrop_image_url(self, provider: str, id: str, **params: Any) -> str:
        return self.build_url(self.BACKDROP_IMAGE_API.format(provider=provider, id=parse.quote(id, safe="")), **params)

    def translate(self, q: str, to: str, engine: str, **params: Any) -> str:
        url = self.build_url(self.TRANSLATE_API, q=q, to=to, engine=engine, **params)
        data = self.get_json(url, require_auth=False)
        if not isinstance(data, dict):
            return q
        return data.get("translated_text") or q

    @staticmethod
    def _query_value(value: Any) -> Any:
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
            return ",".join(str(item) for item in value)
        return value
