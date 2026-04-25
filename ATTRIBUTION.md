# Attribution

This repository is a migration and integration project for Plex Custom Metadata Providers.

It is based on and includes code adapted from:

- `metatube-community/metatube-plex-plugins`
  - Upstream: https://github.com/metatube-community/metatube-plex-plugins
  - License: MIT
  - Local base commit used during this migration: `e5aa36940103fc89fc7599611f987a36789de31c`

It also uses the MetaTube Go SDK and scraping engine from:

- `metatube-community/metatube-sdk-go`
  - Upstream: https://github.com/metatube-community/metatube-sdk-go
  - License: Apache-2.0
  - Local commit used during this migration: `06ed272b74fdee11c8eebf8de62bf69023a7ede7`

The `provider-go/` implementation embeds and calls the `metatube-sdk-go` engine directly, so the standalone Plex provider can scrape metadata without a separate MetaTube API server.

The original copyrights and licenses remain with their respective authors.
