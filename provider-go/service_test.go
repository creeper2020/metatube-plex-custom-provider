package main

import (
	"encoding/base64"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/lib/pq"
	"gorm.io/datatypes"

	"github.com/metatube-community/metatube-sdk-go/model"
)

func TestFilterMovieResultsProviderFilterThenExact(t *testing.T) {
	service := NewService(Settings{
		EnableMovieProviderFilter: true,
		MovieProviderFilter:       "JAV321,JavBus",
	}, nil)
	movies := []*model.MovieSearchResult{
		{Provider: "FANZA", ID: "juq00907", Number: "JUQ-907"},
		{Provider: "JavBus", ID: "JUQ-907", Number: "JUQ-907"},
		{Provider: "JAV321", ID: "juq00907", Number: "JUQ-907"},
	}

	filtered := service.filterMovieResults(movies, "JUQ-907")

	if got := []string{filtered[0].Provider, filtered[1].Provider}; got[0] != "JAV321" || got[1] != "JavBus" {
		t.Fatalf("unexpected provider order: %#v", got)
	}
}

func TestMovieToMetadataAppliesTemplateAndSubstitutions(t *testing.T) {
	titleTable := base64.StdEncoding.EncodeToString([]byte("OLD=NEW"))
	actorTable := base64.StdEncoding.EncodeToString([]byte("ACTOR A=Actor B"))
	genreTable := base64.StdEncoding.EncodeToString([]byte("DRAMA=Drama B"))
	service := NewService(Settings{
		ProviderIdentifier:      "tv.plex.agents.custom.metatube.movie",
		EnableTitleTemplate:     true,
		TitleTemplate:           "{number} {first_actor} {title}",
		EnableTitleSubstitution: true,
		TitleSubstitutionTable:  titleTable,
		EnableActorSubstitution: true,
		ActorSubstitutionTable:  actorTable,
		EnableGenreSubstitution: true,
		GenreSubstitutionTable:  genreTable,
	}, nil)
	movie := &model.MovieInfo{
		ID:          "id",
		Provider:    "FANZA",
		Number:      "ABC-123",
		Title:       "OLD title",
		Actors:      pq.StringArray{"Actor A"},
		Genres:      pq.StringArray{"Drama"},
		ReleaseDate: datatypes.Date(time.Date(2024, 1, 2, 0, 0, 0, 0, time.UTC)),
	}
	request := httptest.NewRequest("GET", "http://127.0.0.1:8080/", nil)

	metadata := service.movieToMetadata(request, movie, SingleRef("FANZA", "id", false), "")

	if metadata.Title != "ABC-123 Actor B NEW title" {
		t.Fatalf("unexpected title: %q", metadata.Title)
	}
	if metadata.Role[0].Tag != "Actor B" {
		t.Fatalf("unexpected actor: %#v", metadata.Role)
	}
	if metadata.Genre[0].Tag != "Drama B" {
		t.Fatalf("unexpected genre: %#v", metadata.Genre)
	}
}

func TestMatchMetadataCarriesBadgeInRatingKey(t *testing.T) {
	service := NewService(Settings{ProviderIdentifier: "tv.plex.agents.custom.metatube.movie", ManualLimit: 10}, nil)
	request := httptest.NewRequest("GET", "http://127.0.0.1:8080/", nil)
	movies := []*model.MovieSearchResult{
		{Provider: "FANZA", ID: "juq00907", Number: "JUQ-907", Title: "Title"},
	}

	metadata := service.matchMetadata(request, movies, "JUQ-907", true, true)
	ref, err := DecodeRatingKey(metadata[0].RatingKey)
	if err != nil {
		t.Fatal(err)
	}
	if !ref.Badge {
		t.Fatal("expected badge flag in ratingKey")
	}
}
