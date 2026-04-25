"""Minimal HTTP server for Plex Custom Metadata Providers."""

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib import parse

from .api_client import APIError
from .config import Settings
from .plex import MATCH_PATH, METADATA_PATH
from .service import ProviderService


class ProviderHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class ProviderRequestHandler(BaseHTTPRequestHandler):
    service: ProviderService

    server_version = "MetaTubeProvider/0.1"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = parse.urlparse(self.path)
        path = request_path(parsed.path, self.service.settings)
        if path is None:
            self.send_error_json(HTTPStatus.NOT_FOUND, "not found")
            return

        try:
            if path in ("", "/"):
                self.send_json(self.service.provider())
                return

            if path == "/health":
                self.send_json({"status": "ok"})
                return

            if path.startswith(f"{METADATA_PATH}/"):
                suffix = path[len(METADATA_PATH) + 1:]
                if suffix.endswith("/images"):
                    rating_key = suffix[:-len("/images")]
                    self.send_json(self.service.images(rating_key))
                    return
                if suffix.endswith("/children") or suffix.endswith("/grandchildren"):
                    self.send_json(empty_container(self.service.settings.provider_identifier))
                    return
                rating_key = suffix.split("/", 1)[0]
                language = plex_value(self.headers, parsed.query, "X-Plex-Language")
                self.send_json(self.service.metadata(rating_key, language))
                return
        except ValueError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except APIError as exc:
            self.send_error_json(HTTPStatus.BAD_GATEWAY, str(exc))
            return
        except Exception as exc:  # pragma: no cover - runtime safety net
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = parse.urlparse(self.path)
        path = request_path(parsed.path, self.service.settings)
        if path is None:
            self.send_error_json(HTTPStatus.NOT_FOUND, "not found")
            return

        try:
            if path == MATCH_PATH:
                body = self.read_json_body()
                language = plex_value(self.headers, parsed.query, "X-Plex-Language")
                self.send_json(self.service.match(body, language))
                return
        except ValueError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except APIError as exc:
            self.send_error_json(HTTPStatus.BAD_GATEWAY, str(exc))
            return
        except Exception as exc:  # pragma: no cover - runtime safety net
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
            return

        self.send_error_json(HTTPStatus.NOT_FOUND, "not found")

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("request body is not valid JSON") from exc
        if not isinstance(body, dict):
            raise ValueError("request body must be a JSON object")
        return body

    def send_json(self, body: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"error": status.phrase, "message": message}, status)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def strip_mount(path: str) -> str:
    if path == "/movie":
        return "/"
    if path.startswith("/movie/"):
        return path[len("/movie"):]
    return path


def request_path(path: str, settings: Settings) -> str | None:
    prefix = settings.path_prefix
    if prefix:
        if path == prefix:
            path = "/"
        elif path.startswith(f"{prefix}/"):
            path = path[len(prefix):] or "/"
        else:
            return None

    return strip_mount(path)


def plex_value(headers: Any, query: str, name: str) -> str | None:
    header_value = headers.get(name)
    if header_value:
        return header_value

    query_values = parse.parse_qs(query)
    values = query_values.get(name)
    return values[0] if values else None


def empty_container(identifier: str) -> dict[str, Any]:
    return {
        "MediaContainer": {
            "offset": 0,
            "totalSize": 0,
            "identifier": identifier,
            "size": 0,
            "Metadata": [],
        },
    }


def create_server(settings: Settings) -> ThreadingHTTPServer:
    service = ProviderService(settings)

    class Handler(ProviderRequestHandler):
        pass

    Handler.service = service
    return ProviderHTTPServer((settings.host, settings.port), Handler)


def main() -> None:
    settings = Settings.from_env()
    server = create_server(settings)
    print(f"MetaTube provider listening on http://{settings.host}:{settings.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
