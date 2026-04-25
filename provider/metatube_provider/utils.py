"""Small utilities shared by the provider."""

from __future__ import annotations

import base64
import os
import re
from datetime import date, datetime
from urllib import parse


DEFAULT_COUNTRY = "Japan"
DEFAULT_CONTENT_RATING = "JP-18+"
DEFAULT_TITLE_TEMPLATE = "{number} {title}"
DEFAULT_ORIGINALLY_AVAILABLE_AT = "1900-01-01"
SUBTITLE_EXTENSIONS = (
    ".utf", ".utf8", ".utf-8", ".srt", ".smi", ".rt", ".ssa", ".aqt",
    ".jss", ".ass", ".idx", ".sub", ".txt", ".psb", ".vtt",
)
VIDEO_EXTENSIONS = (
    ".3g2", ".3gp", ".asf", ".asx", ".avc", ".avi", ".avs", ".bivx",
    ".bup", ".divx", ".dv", ".dvr-ms", ".evo", ".fli", ".flv", ".m2t",
    ".m2ts", ".m2v", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg",
    ".mts", ".nsv", ".nuv", ".ogm", ".ogv", ".tp", ".pva", ".qt",
    ".rm", ".rmvb", ".sdp", ".svq3", ".strm", ".ts", ".ty", ".vdr",
    ".viv", ".vob", ".vp3", ".wmv", ".wpl", ".wtv", ".xsp", ".xvid",
    ".webm",
)


def parse_filename(filename: str) -> str:
    return os.path.basename(parse.unquote(filename or ""))


def parse_filename_without_ext(filename: str) -> str:
    return os.path.splitext(parse_filename(filename))[0]


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    if not match:
        return None
    try:
        parsed = datetime.strptime(match.group(0), "%Y-%m-%d").date()
    except ValueError:
        return None
    if parsed.year < 1900:
        return None
    return parsed


def date_string(value: str | None) -> str:
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else DEFAULT_ORIGINALLY_AVAILABLE_AT


def year(value: str | None) -> int | None:
    parsed = parse_date(value)
    return parsed.year if parsed else None


def parse_list(value: str, sep: str = ",") -> list[str]:
    return [item.strip().upper() for item in value.split(sep) if item.strip()]


def parse_table(value: str, sep: str = ",", b64: bool = False, origin_key: bool = False) -> dict[str, str]:
    table: dict[str, str] = {}
    if not value:
        return table
    if b64:
        value = base64.b64decode(value).decode("utf-8")
    for item in value.split(sep):
        item = item.strip()
        if "=" not in item or item.startswith("="):
            continue
        key, replacement = item.split("=", 1)
        table[key if origin_key else key.upper()] = replacement
    return table


def table_substitute(table: dict[str, str], items: Iterable[str]) -> list[str]:
    return [table.get(item.upper(), item) for item in items]


def has_embedded_chinese_subtitle(video_name: str) -> bool:
    name, ext = os.path.splitext(os.path.basename(video_name))
    if ext.lower() not in VIDEO_EXTENSIONS:
        return False

    values = [item.upper() for item in re.split(r"[-_\s]", name)]
    return "中文字幕" in name or any(tag in values for tag in ("C", "UC", "CH"))


def has_external_chinese_subtitle(video_name: str) -> bool:
    if not video_name or not os.path.exists(video_name):
        return False

    basename, ext = os.path.splitext(os.path.basename(video_name))
    if ext.lower() not in VIDEO_EXTENSIONS:
        return False

    pattern = re.compile(r"\.(ch[ist]|zho?(-(cn|hk|sg|tw))?)\.(ass|srt|ssa|smi|sub|idx|psb|vtt)$", re.IGNORECASE)
    try:
        filenames = os.listdir(os.path.dirname(video_name))
    except OSError:
        return False

    for filename in filenames:
        if pattern.search(filename) and pattern.sub("", filename).upper() == basename.upper():
            return True
    return False


def has_chinese_subtitle(video_name: str) -> bool:
    return has_embedded_chinese_subtitle(video_name) or has_external_chinese_subtitle(video_name)
