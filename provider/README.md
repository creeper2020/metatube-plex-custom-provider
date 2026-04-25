# MetaTube Custom Metadata Provider

This is the Plex `Custom Metadata Providers` migration path for MetaTube. It runs as a standalone HTTP service and does not depend on the legacy Plex Python plug-in runtime.

## Scope

- Movie metadata provider only.
- Implements `/library/metadata/matches`.
- Implements `/library/metadata/{ratingKey}`.
- Reuses the existing MetaTube backend for movie search, movie details, images, actor images, and translations.
- When an exact catalog number matches multiple sources, the first match is a merged candidate; manual matching still keeps the single-source candidates as fallbacks.
- Keeps most legacy preferences as environment variables.

Merge rules:

- Conflicting scalar fields such as title, poster, background, and studio use the preferred source.
- List fields such as actors, genres, and preview images are de-duplicated in source order.
- Rating and duration use the first valid value.
- Preferred source order can be controlled with `METATUBE_MOVIE_PROVIDER_FILTER`.

Collections, reviews, and trailer extras are not migrated yet. Collections require a `collection` feature plus a children endpoint; reviews and trailer extras do not currently have stable fields in Plex's public Metadata Provider schema.

## Run

```bash
cd provider
export METATUBE_API_SERVER="https://api.metatube.internal"
export METATUBE_API_TOKEN="your-token"
python -m metatube_provider
```

The provider listens on `http://127.0.0.1:8080` by default. If PMS runs in Docker or on another host, set `METATUBE_HOST` to an address PMS can reach.

You can also put configuration in `provider/.env`. That file is ignored by `.gitignore`, and the service reads it automatically on startup.

For public deployment, enable a path token:

```env
METATUBE_HOST=0.0.0.0
METATUBE_AUTH_PATH=_metatube
METATUBE_AUTH_TOKEN=your-long-random-token
```

Then register this URL in Plex:

```text
http://your-host:8080/_metatube/your-long-random-token
```

Requests without the token prefix return 404.

Docker:

```bash
cd provider
docker build -t metatube-provider .
docker run --rm -p 8080:8080 \
  -e METATUBE_API_SERVER="https://api.metatube.internal" \
  -e METATUBE_API_TOKEN="your-token" \
  metatube-provider
```

## Register in Plex

Plex Media Server 1.43.0 or newer is required.

1. Open Plex Web.
2. Go to `Settings -> Metadata Agents -> Add Provider`.
3. Enter the provider URL, for example `http://127.0.0.1:8080`. If the provider runs in Docker or on another host, use an address reachable from PMS.
4. Create a Metadata Agent and set `MetaTube Movie Provider` as the primary provider.
5. Create a Movie library and choose that Agent in the Advanced tab.

## Test

```bash
python -m unittest discover -s tests -t .
```
