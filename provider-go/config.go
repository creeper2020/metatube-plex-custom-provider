package main

import (
	"os"
	"strconv"
	"strings"
	"time"
)

type Settings struct {
	Host                        string
	Port                        string
	DSN                         string
	ProviderIdentifier          string
	ProviderTitle               string
	AuthPath                    string
	AuthToken                   string
	RequestTimeout              time.Duration
	ManualLimit                 int
	EnableActorImages           bool
	EnableDirectors             bool
	EnableRatings               bool
	EnableRealActorNames        bool
	EnableBadges                bool
	BadgeURL                    string
	EnableMovieProviderFilter   bool
	MovieProviderFilter         string
	EnableTitleTemplate         bool
	TitleTemplate               string
	EnableTitleSubstitution     bool
	TitleSubstitutionTable      string
	EnableActorSubstitution     bool
	ActorSubstitutionTable      string
	EnableGenreSubstitution     bool
	GenreSubstitutionTable      string
	TranslationMode             string
	TranslationEngine           string
	TranslationEngineParameters string
}

func LoadSettings() Settings {
	return Settings{
		Host:                        getenv("METATUBE_HOST", "127.0.0.1"),
		Port:                        getenv("METATUBE_PORT", "8080"),
		DSN:                         getenv("METATUBE_DSN", "/home/plex/metatube-provider-go.db"),
		ProviderIdentifier:          getenv("METATUBE_PROVIDER_IDENTIFIER", "tv.plex.agents.custom.metatube.movie"),
		ProviderTitle:               getenv("METATUBE_PROVIDER_TITLE", "MetaTube Movie Provider"),
		AuthPath:                    getenv("METATUBE_AUTH_PATH", "_metatube"),
		AuthToken:                   getenv("METATUBE_AUTH_TOKEN", ""),
		RequestTimeout:              getduration("METATUBE_REQUEST_TIMEOUT", 60*time.Second),
		ManualLimit:                 getint("METATUBE_MANUAL_LIMIT", 10),
		EnableActorImages:           getbool("METATUBE_ENABLE_ACTOR_IMAGES", true),
		EnableDirectors:             getbool("METATUBE_ENABLE_DIRECTORS", true),
		EnableRatings:               getbool("METATUBE_ENABLE_RATINGS", true),
		EnableRealActorNames:        getbool("METATUBE_ENABLE_REAL_ACTOR_NAMES", false),
		EnableBadges:                getbool("METATUBE_ENABLE_BADGES", false),
		BadgeURL:                    getenv("METATUBE_BADGE_URL", "zimu.png"),
		EnableMovieProviderFilter:   getbool("METATUBE_ENABLE_MOVIE_PROVIDER_FILTER", false),
		MovieProviderFilter:         getenv("METATUBE_MOVIE_PROVIDER_FILTER", ""),
		EnableTitleTemplate:         getbool("METATUBE_ENABLE_TITLE_TEMPLATE", false),
		TitleTemplate:               getenv("METATUBE_TITLE_TEMPLATE", "{number} {title}"),
		EnableTitleSubstitution:     getbool("METATUBE_ENABLE_TITLE_SUBSTITUTION", false),
		TitleSubstitutionTable:      getenv("METATUBE_TITLE_SUBSTITUTION_TABLE", ""),
		EnableActorSubstitution:     getbool("METATUBE_ENABLE_ACTOR_SUBSTITUTION", false),
		ActorSubstitutionTable:      getenv("METATUBE_ACTOR_SUBSTITUTION_TABLE", ""),
		EnableGenreSubstitution:     getbool("METATUBE_ENABLE_GENRE_SUBSTITUTION", false),
		GenreSubstitutionTable:      getenv("METATUBE_GENRE_SUBSTITUTION_TABLE", ""),
		TranslationMode:             getenv("METATUBE_TRANSLATION_MODE", "Disabled"),
		TranslationEngine:           getenv("METATUBE_TRANSLATION_ENGINE", "Baidu"),
		TranslationEngineParameters: getenv("METATUBE_TRANSLATION_ENGINE_PARAMETERS", ""),
	}
}

func (s Settings) PathPrefix() string {
	token := strings.Trim(s.AuthToken, "/")
	if token == "" {
		return ""
	}
	path := strings.Trim(s.AuthPath, "/")
	if path == "" {
		return "/" + token
	}
	return "/" + path + "/" + token
}

func (s Settings) TranslationHas(mode string) bool {
	flags := map[string]int{
		"Disabled":                   0,
		"Title":                      1,
		"Summary":                    2,
		"Reviews":                    4,
		"Title and Summary":          3,
		"Title, Summary and Reviews": 7,
	}
	return flags[s.TranslationMode]&flags[mode] != 0
}

func getenv(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}

func getint(name string, fallback int) int {
	value := os.Getenv(name)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func getbool(name string, fallback bool) bool {
	value := strings.ToLower(strings.TrimSpace(os.Getenv(name)))
	if value == "" {
		return fallback
	}
	return value == "1" || value == "true" || value == "yes" || value == "on"
}

func getduration(name string, fallback time.Duration) time.Duration {
	value := os.Getenv(name)
	if value == "" {
		return fallback
	}
	parsed, err := time.ParseDuration(value)
	if err == nil {
		return parsed
	}
	seconds, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return time.Duration(seconds) * time.Second
}
