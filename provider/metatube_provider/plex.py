"""Plex Custom Metadata Provider response builders."""

from __future__ import annotations

from typing import Any

from . import __version__


METADATA_PATH = "/library/metadata"
MATCH_PATH = "/library/metadata/matches"


def provider_response(identifier: str, title: str, path_prefix: str = "") -> dict[str, Any]:
    return {
        "MediaProvider": {
            "identifier": identifier,
            "title": title,
            "version": __version__,
            "Types": [
                {
                    "type": 1,
                    "Scheme": [{"scheme": identifier}],
                },
            ],
            "Feature": [
                {"type": "metadata", "key": prefixed_path(path_prefix, METADATA_PATH)},
                {"type": "match", "key": prefixed_path(path_prefix, MATCH_PATH)},
            ],
        },
    }


def media_container(identifier: str, metadata: list[dict[str, Any]], offset: int = 0, total_size: int | None = None) -> dict[str, Any]:
    total = len(metadata) if total_size is None else total_size
    return {
        "MediaContainer": {
            "offset": offset,
            "totalSize": total,
            "identifier": identifier,
            "size": len(metadata),
            "Metadata": metadata,
        },
    }


def image_container(identifier: str, images: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "MediaContainer": {
            "offset": 0,
            "totalSize": len(images),
            "identifier": identifier,
            "size": len(images),
            "Image": images,
        },
    }


def prefixed_path(path_prefix: str, path: str) -> str:
    prefix = path_prefix.rstrip("/")
    if not prefix:
        return path
    return f"{prefix}{path}"
