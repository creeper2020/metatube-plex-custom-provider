"""Provider ID and ratingKey helpers."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any
from urllib import parse


RATING_KEY_PREFIX = "mt_"


@dataclass(frozen=True)
class ProviderID:
    provider: str
    id: str
    position: float | None = None
    update: bool | None = None
    badge: bool = False

    @classmethod
    def parse_legacy(cls, value: str) -> "ProviderID":
        parts = value.split(":")
        if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
            raise ValueError(f"invalid provider id: {value}")

        return cls(
            provider=parts[0],
            id=parse.unquote(parts[1]),
            position=to_float(parts[2]) if len(parts) >= 3 else None,
            update=to_bool(parts[3]) if len(parts) >= 4 else None,
        )

    @classmethod
    def try_parse_legacy(cls, value: str | None) -> "ProviderID | None":
        if not value:
            return None
        try:
            return cls.parse_legacy(value)
        except ValueError:
            return None

    def legacy(self) -> str:
        values = [self.provider, parse.quote(self.id)]
        if self.position is not None:
            values.append(str(round(self.position, 2)))
        if self.update is not None:
            if self.position is None:
                values.append("")
            values.append("1" if self.update else "0")
        return ":".join(values)


@dataclass(frozen=True)
class MergedProviderID:
    sources: tuple[ProviderID, ...]
    badge: bool = False

    @property
    def primary(self) -> ProviderID:
        return self.sources[0]

    def legacy(self) -> str:
        return "merge:" + ",".join(source.legacy() for source in self.sources)


ProviderRef = ProviderID | MergedProviderID


def encode_rating_key(pid: ProviderRef) -> str:
    if isinstance(pid, MergedProviderID):
        payload: dict[str, Any] = {
            "m": [provider_payload(source) for source in pid.sources],
        }
        if pid.badge:
            payload["b"] = True
        return encode_payload(payload)

    payload: dict[str, Any] = {
        "p": pid.provider,
        "i": pid.id,
    }
    if pid.position is not None:
        payload["o"] = round(pid.position, 2)
    if pid.update is not None:
        payload["u"] = pid.update
    if pid.badge:
        payload["b"] = True
    return encode_payload(payload)


def encode_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"{RATING_KEY_PREFIX}{encoded}"


def decode_rating_key(rating_key: str) -> ProviderRef:
    if not rating_key.startswith(RATING_KEY_PREFIX):
        raise ValueError(f"invalid MetaTube ratingKey: {rating_key}")

    encoded = rating_key[len(RATING_KEY_PREFIX):]
    padded = encoded + ("=" * (-len(encoded) % 4))
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid MetaTube ratingKey: {rating_key}") from exc

    sources = payload.get("m")
    if isinstance(sources, list):
        decoded_sources = tuple(decode_provider_payload(source) for source in sources)
        if not decoded_sources:
            raise ValueError(f"invalid MetaTube merged ratingKey payload: {rating_key}")
        return MergedProviderID(sources=decoded_sources, badge=bool(payload.get("b")))

    return decode_provider_payload(payload, rating_key=rating_key)


def provider_payload(pid: ProviderID) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "p": pid.provider,
        "i": pid.id,
    }
    if pid.position is not None:
        payload["o"] = round(pid.position, 2)
    if pid.update is not None:
        payload["u"] = pid.update
    return payload


def decode_provider_payload(payload: Any, rating_key: str | None = None) -> ProviderID:
    if not isinstance(payload, dict):
        raise ValueError("invalid MetaTube ratingKey source payload")

    provider = payload.get("p")
    id = payload.get("i")
    if not isinstance(provider, str) or not provider or not isinstance(id, str) or not id:
        suffix = f": {rating_key}" if rating_key else ""
        raise ValueError(f"invalid MetaTube ratingKey payload{suffix}")

    return ProviderID(
        provider=provider,
        id=id,
        position=to_float(payload.get("o")),
        update=payload.get("u") if isinstance(payload.get("u"), bool) else None,
        badge=bool(payload.get("b")),
    )


def parse_guid(guid: str, provider_identifier: str) -> ProviderRef | None:
    prefix = f"{provider_identifier}://movie/"
    if guid.startswith(prefix):
        return decode_rating_key(guid[len(prefix):])

    if guid.startswith("metatube://"):
        parts = guid[len("metatube://"):].split("/", 1)
        if len(parts) == 2 and parts[0] and parts[1]:
            return ProviderID(provider=parts[0], id=parse.unquote(parts[1]))

    return ProviderID.try_parse_legacy(guid)


def to_float(value: Any) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return None
    if value in ("1", "t", "T", "true", "True", "TRUE"):
        return True
    if value in ("0", "f", "F", "false", "False", "FALSE"):
        return False
    return None
