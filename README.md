# MetaTube Plex Custom Provider

[中文文档（Chinese）](./README_ZH.md)

A standalone MetaTube scraper service for the **Plex Custom Metadata Providers API**.

This project extracts the Plex plugin workflow from `metatube-community/metatube-plex-plugins` and ships it as an HTTP provider. It embeds the scraping engine from `metatube-community/metatube-sdk-go` directly under `provider-go/`, so Plex can call this provider service directly without deploying a separate MetaTube API server.

For source attribution and license details, see [ATTRIBUTION.md](./ATTRIBUTION.md).

## Status

- Primary implementation: [`provider-go/`](./provider-go)
- Runtime: single Go binary
- Recommended deployment: localhost + reverse proxy (HTTPS)
- Plex requirement: a Plex version that supports **Custom Metadata Providers**
- Trailer output: currently not included

## What It Supports

- Provider root document for Plex Custom Metadata Providers
- Manual matching endpoint: `POST /library/metadata/matches`
- Metadata detail endpoint: `GET /library/metadata/{ratingKey}`
- Image list endpoint: `GET /library/metadata/{ratingKey}/images`
- Poster / background / actor-image proxying
- Multi-source search, exact number filtering, merged ranking
- Source-level filtering and ordering
- Title templates
- Title / actor / genre substitution tables
- AVBASE real-name actor replacement
- Title and summary translation
- Directors, studios, genres, actor avatars, ratings
- Chinese-subtitle detection and cover badges
- Path-token authentication
- Reverse-proxy-aware public URL generation

## Repository Structure

```text
provider-go/            Main Go provider implementation
provider/               Early Python provider prototype (kept for reference)
MetaTube.bundle/        Legacy upstream Plex plugin code (reference only)
MetaTubeHelper.bundle/  Legacy upstream helper plugin code (reference only)
ATTRIBUTION.md          Upstream source and SDK attribution
PROJECT_MEMORY.md       Project maintenance notes
```

## Prerequisites

`provider-go/go.mod` uses a local replace directive for `metatube-sdk-go`.

Recommended local directory layout:

```text
workspace/
  metatube-sdk-go/
  metatube-plex-custom-provider/
```

If your layout differs, update this entry in [`provider-go/go.mod`](./provider-go/go.mod):

```go
replace github.com/metatube-community/metatube-sdk-go => ../../metatube-sdk-go
```

## Build

```sh
cd workspace/metatube-plex-custom-provider/provider-go
go test ./...
go build -o metatube-plex-provider .
```

## Run

Bind to localhost and expose externally through a reverse proxy:

```sh
METATUBE_HOST=127.0.0.1 \
METATUBE_PORT=8080 \
METATUBE_DSN=/path/to/metatube-provider-go.db \
METATUBE_AUTH_TOKEN='replace-with-a-random-token' \
./metatube-plex-provider
```

Provider URL format:

```text
https://your-domain.example/_metatube/<token>
```

`<token>` is `METATUBE_AUTH_TOKEN`. Do **not** commit real tokens.

## Add Provider in Plex

In Plex, open **Custom Metadata Providers** and add:

```text
https://your-domain.example/_metatube/<token>
```

Then select this provider for your movie library and run match/refresh.

## Reverse Proxy Example (Nginx)

The provider uses `X-Forwarded-Proto` and `X-Forwarded-Host` when generating image URLs returned to Plex.

```nginx
location /_metatube/ {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

For internet-facing deployments, expose HTTPS only and keep port `8080` private.

## Common Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `METATUBE_HOST` | `127.0.0.1` | Listen address |
| `METATUBE_PORT` | `8080` | Listen port |
| `METATUBE_DSN` | `/home/plex/metatube-provider-go.db` | SQLite or PostgreSQL DSN |
| `METATUBE_AUTH_PATH` | `_metatube` | Auth path prefix |
| `METATUBE_AUTH_TOKEN` | empty | Path auth token |
| `METATUBE_REQUEST_TIMEOUT` | `60s` | Scrape request timeout |
| `METATUBE_MANUAL_LIMIT` | `10` | Manual match result limit |
| `METATUBE_ENABLE_ACTOR_IMAGES` | `true` | Include actor avatars |
| `METATUBE_ENABLE_DIRECTORS` | `true` | Include directors |
| `METATUBE_ENABLE_RATINGS` | `true` | Include ratings |
| `METATUBE_ENABLE_REAL_ACTOR_NAMES` | `false` | Replace with AVBASE real actor names |
| `METATUBE_ENABLE_BADGES` | `false` | Add subtitle badges |
| `METATUBE_BADGE_URL` | `zimu.png` | Badge image URL |
| `METATUBE_ENABLE_MOVIE_PROVIDER_FILTER` | `false` | Enable source filtering and ordering |
| `METATUBE_MOVIE_PROVIDER_FILTER` | empty | Provider order, e.g. `FANZA,JavBus,JAV321` |
| `METATUBE_ENABLE_TITLE_TEMPLATE` | `false` | Enable title template |
| `METATUBE_TITLE_TEMPLATE` | `{number} {title}` | Title template |
| `METATUBE_ENABLE_TITLE_SUBSTITUTION` | `false` | Enable title substitution |
| `METATUBE_TITLE_SUBSTITUTION_TABLE` | empty | Base64 table, each line `old=new` |
| `METATUBE_ENABLE_ACTOR_SUBSTITUTION` | `false` | Enable actor substitution |
| `METATUBE_ACTOR_SUBSTITUTION_TABLE` | empty | Base64 table, each line `old=new` |
| `METATUBE_ENABLE_GENRE_SUBSTITUTION` | `false` | Enable genre substitution |
| `METATUBE_GENRE_SUBSTITUTION_TABLE` | empty | Base64 table, each line `old=new` |
| `METATUBE_TRANSLATION_MODE` | `Disabled` | Translation scope |
| `METATUBE_TRANSLATION_ENGINE` | `Baidu` | Translation engine |
| `METATUBE_TRANSLATION_ENGINE_PARAMETERS` | empty | Translation engine parameters |

Supported title-template fields:

```text
{provider} {id} {number} {title} {series} {maker} {label} {director} {actors} {first_actor} {year} {date}
```

## Verification

```sh
cd provider-go
go test ./...
```

Health check example:

```sh
curl http://127.0.0.1:8080/_metatube/<token>/health
```

## Troubleshooting

- If `go test` fails with `replacement directory ../../metatube-sdk-go does not exist`, fix the local repo layout or update the `replace` directive in `provider-go/go.mod`.
- If module downloads fail in restricted environments, set an accessible `GOPROXY` or use your internal Go proxy.

## License and Attribution

This repository is a migration/integration project that preserves upstream attribution:

- `metatube-community/metatube-plex-plugins`: MIT License
- `metatube-community/metatube-sdk-go`: Apache-2.0 License

See [ATTRIBUTION.md](./ATTRIBUTION.md) for detailed source repositories, commit references, and notes.
