"""Runtime configuration for the MetaTube provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


TRANSLATION_DISABLED = "Disabled"
TRANSLATION_TITLE = "Title"
TRANSLATION_SUMMARY = "Summary"
TRANSLATION_REVIEWS = "Reviews"
TRANSLATION_TITLE_SUMMARY = "Title and Summary"
TRANSLATION_TITLE_SUMMARY_REVIEWS = "Title, Summary and Reviews"

TRANSLATION_MODE_FLAGS = {
    TRANSLATION_DISABLED: 0b0000,
    TRANSLATION_TITLE: 0b0001,
    TRANSLATION_SUMMARY: 0b0010,
    TRANSLATION_REVIEWS: 0b0100,
    TRANSLATION_TITLE_SUMMARY: 0b0011,
    TRANSLATION_TITLE_SUMMARY_REVIEWS: 0b0111,
}


@dataclass(frozen=True)
class Settings:
    api_server: str = "https://api.metatube.internal"
    api_token: str = ""
    host: str = "127.0.0.1"
    port: int = 8080
    provider_identifier: str = "tv.plex.agents.custom.metatube.movie"
    provider_title: str = "MetaTube Movie Provider"
    auth_path: str = "_metatube"
    auth_token: str = ""
    request_timeout: float = 20.0
    manual_limit: int = 10
    enable_directors: bool = True
    enable_ratings: bool = True
    enable_real_actor_names: bool = False
    enable_actor_images: bool = True
    enable_badges: bool = False
    badge_url: str = "zimu.png"
    enable_movie_provider_filter: bool = False
    movie_provider_filter: str = ""
    enable_title_template: bool = False
    title_template: str = "{number} {title}"
    enable_title_substitution: bool = False
    title_substitution_table: str = ""
    enable_actor_substitution: bool = False
    actor_substitution_table: str = ""
    enable_genre_substitution: bool = False
    genre_substitution_table: str = ""
    translation_mode: str = TRANSLATION_DISABLED
    translation_engine: str = "Baidu"
    translation_engine_parameters: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        load_env_file(os.environ.get("METATUBE_ENV_FILE", ".env"))
        return cls(
            api_server=getenv("METATUBE_API_SERVER", cls.api_server),
            api_token=getenv("METATUBE_API_TOKEN", cls.api_token),
            host=getenv("METATUBE_HOST", cls.host),
            port=getint("METATUBE_PORT", cls.port),
            provider_identifier=getenv("METATUBE_PROVIDER_IDENTIFIER", cls.provider_identifier),
            provider_title=getenv("METATUBE_PROVIDER_TITLE", cls.provider_title),
            auth_path=getenv("METATUBE_AUTH_PATH", cls.auth_path),
            auth_token=getenv("METATUBE_AUTH_TOKEN", cls.auth_token),
            request_timeout=getfloat("METATUBE_REQUEST_TIMEOUT", cls.request_timeout),
            manual_limit=getint("METATUBE_MANUAL_LIMIT", cls.manual_limit),
            enable_directors=getbool("METATUBE_ENABLE_DIRECTORS", cls.enable_directors),
            enable_ratings=getbool("METATUBE_ENABLE_RATINGS", cls.enable_ratings),
            enable_real_actor_names=getbool("METATUBE_ENABLE_REAL_ACTOR_NAMES", cls.enable_real_actor_names),
            enable_actor_images=getbool("METATUBE_ENABLE_ACTOR_IMAGES", cls.enable_actor_images),
            enable_badges=getbool("METATUBE_ENABLE_BADGES", cls.enable_badges),
            badge_url=getenv("METATUBE_BADGE_URL", cls.badge_url),
            enable_movie_provider_filter=getbool(
                "METATUBE_ENABLE_MOVIE_PROVIDER_FILTER",
                cls.enable_movie_provider_filter,
            ),
            movie_provider_filter=getenv("METATUBE_MOVIE_PROVIDER_FILTER", cls.movie_provider_filter),
            enable_title_template=getbool("METATUBE_ENABLE_TITLE_TEMPLATE", cls.enable_title_template),
            title_template=getenv("METATUBE_TITLE_TEMPLATE", cls.title_template),
            enable_title_substitution=getbool(
                "METATUBE_ENABLE_TITLE_SUBSTITUTION",
                cls.enable_title_substitution,
            ),
            title_substitution_table=getenv("METATUBE_TITLE_SUBSTITUTION_TABLE", cls.title_substitution_table),
            enable_actor_substitution=getbool(
                "METATUBE_ENABLE_ACTOR_SUBSTITUTION",
                cls.enable_actor_substitution,
            ),
            actor_substitution_table=getenv("METATUBE_ACTOR_SUBSTITUTION_TABLE", cls.actor_substitution_table),
            enable_genre_substitution=getbool(
                "METATUBE_ENABLE_GENRE_SUBSTITUTION",
                cls.enable_genre_substitution,
            ),
            genre_substitution_table=getenv("METATUBE_GENRE_SUBSTITUTION_TABLE", cls.genre_substitution_table),
            translation_mode=getenv("METATUBE_TRANSLATION_MODE", cls.translation_mode),
            translation_engine=getenv("METATUBE_TRANSLATION_ENGINE", cls.translation_engine),
            translation_engine_parameters=getenv(
                "METATUBE_TRANSLATION_ENGINE_PARAMETERS",
                cls.translation_engine_parameters,
            ),
        )

    def translation_has(self, mode: str) -> bool:
        configured = TRANSLATION_MODE_FLAGS.get(self.translation_mode, 0)
        requested = TRANSLATION_MODE_FLAGS[mode]
        return bool(configured & requested)

    @property
    def path_prefix(self) -> str:
        token = self.auth_token.strip("/")
        if not token:
            return ""

        path = self.auth_path.strip("/")
        if not path:
            return f"/{token}"
        return f"/{path}/{token}"


def getenv(name: str, default: str) -> str:
    return os.environ.get(name, default)


def load_env_file(path: str) -> None:
    env_path = Path(path)
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def getbool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def getint(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def getfloat(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default
