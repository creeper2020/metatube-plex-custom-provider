package main

import (
	"net/http"
	"net/url"
	"path"
	"strings"
)

const (
	metadataPath = "/library/metadata"
	matchPath    = "/library/metadata/matches"
)

type ProviderResponse struct {
	MediaProvider MediaProvider `json:"MediaProvider"`
}

type MediaProvider struct {
	Identifier string            `json:"identifier"`
	Title      string            `json:"title"`
	Version    string            `json:"version"`
	Types      []ProviderType    `json:"Types"`
	Feature    []ProviderFeature `json:"Feature"`
}

type ProviderType struct {
	Type   int              `json:"type"`
	Scheme []map[string]any `json:"Scheme"`
}

type ProviderFeature struct {
	Type string `json:"type"`
	Key  string `json:"key"`
}

type MediaContainer struct {
	Offset     int        `json:"offset"`
	TotalSize  int        `json:"totalSize"`
	Identifier string     `json:"identifier"`
	Size       int        `json:"size"`
	Metadata   []Metadata `json:"Metadata,omitempty"`
	Image      []Image    `json:"Image,omitempty"`
}

type MediaContainerResponse struct {
	MediaContainer MediaContainer `json:"MediaContainer"`
}

type Metadata struct {
	RatingKey             string       `json:"ratingKey"`
	Key                   string       `json:"key"`
	GUID                  string       `json:"guid"`
	Type                  string       `json:"type"`
	Title                 string       `json:"title"`
	OriginalTitle         string       `json:"originalTitle,omitempty"`
	Summary               string       `json:"summary,omitempty"`
	Tagline               string       `json:"tagline,omitempty"`
	ContentRating         string       `json:"contentRating,omitempty"`
	OriginallyAvailableAt string       `json:"originallyAvailableAt,omitempty"`
	Year                  int          `json:"year,omitempty"`
	Thumb                 string       `json:"thumb,omitempty"`
	Art                   string       `json:"art,omitempty"`
	Image                 []Image      `json:"Image,omitempty"`
	Guid                  []Guid       `json:"Guid,omitempty"`
	Country               []Tag        `json:"Country,omitempty"`
	Genre                 []Tag        `json:"Genre,omitempty"`
	Duration              int          `json:"duration,omitempty"`
	Studio                string       `json:"studio,omitempty"`
	StudioTag             []Tag        `json:"Studio,omitempty"`
	Director              []Tag        `json:"Director,omitempty"`
	Role                  []Role       `json:"Role,omitempty"`
	Rating                []PlexRating `json:"Rating,omitempty"`
}

type Image struct {
	Type string `json:"type"`
	URL  string `json:"url"`
	Alt  string `json:"alt,omitempty"`
}

type Guid struct {
	ID string `json:"id"`
}

type Tag struct {
	Tag string `json:"tag"`
}

type Role struct {
	Tag   string `json:"tag"`
	Order int    `json:"order,omitempty"`
	Thumb string `json:"thumb,omitempty"`
}

type PlexRating struct {
	Image string  `json:"image"`
	Type  string  `json:"type"`
	Value float64 `json:"value"`
}

func ProviderDocument(settings Settings) ProviderResponse {
	prefix := settings.PathPrefix()
	return ProviderResponse{MediaProvider: MediaProvider{
		Identifier: settings.ProviderIdentifier,
		Title:      settings.ProviderTitle,
		Version:    "0.2.0-go",
		Types: []ProviderType{{
			Type:   1,
			Scheme: []map[string]any{{"scheme": settings.ProviderIdentifier}},
		}},
		Feature: []ProviderFeature{
			{Type: "metadata", Key: prefixedPath(prefix, metadataPath)},
			{Type: "match", Key: prefixedPath(prefix, matchPath)},
		},
	}}
}

func Container(identifier string, metadata []Metadata) MediaContainerResponse {
	return MediaContainerResponse{MediaContainer: MediaContainer{
		Offset:     0,
		TotalSize:  len(metadata),
		Identifier: identifier,
		Size:       len(metadata),
		Metadata:   metadata,
	}}
}

func ImageContainer(identifier string, images []Image) MediaContainerResponse {
	return MediaContainerResponse{MediaContainer: MediaContainer{
		Offset:     0,
		TotalSize:  len(images),
		Identifier: identifier,
		Size:       len(images),
		Image:      images,
	}}
}

func prefixedPath(prefix, p string) string {
	prefix = strings.TrimRight(prefix, "/")
	if prefix == "" {
		return p
	}
	return prefix + p
}

func requestPath(rawPath string, settings Settings) (string, bool) {
	prefix := settings.PathPrefix()
	if prefix != "" {
		switch {
		case rawPath == prefix:
			rawPath = "/"
		case strings.HasPrefix(rawPath, prefix+"/"):
			rawPath = strings.TrimPrefix(rawPath, prefix)
		default:
			return "", false
		}
	}
	if rawPath == "/movie" {
		return "/", true
	}
	if strings.HasPrefix(rawPath, "/movie/") {
		return strings.TrimPrefix(rawPath, "/movie"), true
	}
	return rawPath, true
}

func absoluteURL(r *http.Request, settings Settings, parts ...string) string {
	base := settings.PathPrefix()
	for _, part := range parts {
		base = path.Join(base, part)
	}
	if !strings.HasPrefix(base, "/") {
		base = "/" + base
	}
	scheme := r.Header.Get("X-Forwarded-Proto")
	if scheme == "" {
		scheme = "http"
	}
	host := r.Header.Get("X-Forwarded-Host")
	if host == "" {
		host = r.Host
	}
	if host == "" {
		host = "127.0.0.1:" + settings.Port
	}
	return (&url.URL{Scheme: scheme, Host: host, Path: base}).String()
}
