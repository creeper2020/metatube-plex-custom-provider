package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"sort"
	"strings"
	"time"

	"github.com/metatube-community/metatube-sdk-go/engine"
	sdkpid "github.com/metatube-community/metatube-sdk-go/engine/providerid"
	"github.com/metatube-community/metatube-sdk-go/model"
	"github.com/metatube-community/metatube-sdk-go/translate"
)

const (
	defaultCountry       = "Japan"
	defaultContentRating = "JP-18+"
	gfriendsProvider     = "Gfriends"
	avbaseProvider       = "AVBASE"
	translationTitle     = "Title"
	translationSummary   = "Summary"
)

var avbaseSupportedProviders = map[string]bool{
	"DUGA": true, "FANZA": true, "GETCHU": true, "MGS": true, "PCOLLE": true,
}

type Service struct {
	settings Settings
	engine   *engine.Engine
}

func NewService(settings Settings, eng *engine.Engine) *Service {
	return &Service{settings: settings, engine: eng}
}

func (s *Service) Provider() ProviderResponse {
	return ProviderDocument(s.settings)
}

func (s *Service) Match(r *http.Request, body map[string]any) (MediaContainerResponse, error) {
	if intValue(body["type"]) != 1 {
		return Container(s.settings.ProviderIdentifier, nil), nil
	}

	filename, _ := body["filename"].(string)
	badge := hasChineseSubtitle(filename)
	if ref, ok := s.pidFromMatch(body); ok {
		ref = ref.WithBadge(badge)
		movie, err := s.movieInfoForRef(ref)
		if err != nil {
			return MediaContainerResponse{}, err
		}
		return Container(s.settings.ProviderIdentifier, []Metadata{s.movieToMetadata(r, movie, ref, plexLanguage(r))}), nil
	}

	query := s.queryFromMatch(body)
	if query == "" {
		return Container(s.settings.ProviderIdentifier, nil), nil
	}

	results, err := s.engine.SearchMovieAll(query, true)
	if err != nil {
		return MediaContainerResponse{}, err
	}
	results = s.filterMovieResults(results, query)

	manual := intValue(body["manual"]) == 1
	metadata := s.matchMetadata(r, results, query, manual, badge)
	return Container(s.settings.ProviderIdentifier, metadata), nil
}

func (s *Service) Metadata(r *http.Request, ratingKey string) (MediaContainerResponse, error) {
	ref, err := DecodeRatingKey(ratingKey)
	if err != nil {
		return MediaContainerResponse{}, err
	}
	movie, err := s.movieInfoForRef(ref)
	if err != nil {
		return MediaContainerResponse{}, err
	}
	return Container(s.settings.ProviderIdentifier, []Metadata{s.movieToMetadata(r, movie, ref, plexLanguage(r))}), nil
}

func (s *Service) Images(r *http.Request, ratingKey string) (MediaContainerResponse, error) {
	ref, err := DecodeRatingKey(ratingKey)
	if err != nil {
		return MediaContainerResponse{}, err
	}
	movie, err := s.movieInfoForRef(ref)
	if err != nil {
		return MediaContainerResponse{}, err
	}
	title := s.formatMovieTitle(movie)
	return ImageContainer(s.settings.ProviderIdentifier, []Image{
		{Type: "coverPoster", URL: absoluteURL(r, s.settings, "images/movie/primary", ratingKey), Alt: title},
		{Type: "background", URL: absoluteURL(r, s.settings, "images/movie/backdrop", ratingKey), Alt: title},
	}), nil
}

func (s *Service) matchMetadata(r *http.Request, movies []*model.MovieSearchResult, query string, manual bool, badge bool) []Metadata {
	if len(movies) == 0 {
		return nil
	}

	var metadata []Metadata
	if len(exactMovieResults(movies, query)) > 1 {
		metadata = append(metadata, s.mergedSearchResultToMetadata(r, movies, badge))
		if !manual {
			return metadata
		}
	}

	limit := 1
	if manual {
		limit = s.settings.ManualLimit
	}
	for _, movie := range movies {
		if len(metadata) >= limit {
			break
		}
		metadata = append(metadata, s.searchResultToMetadata(r, movie, badge))
	}
	return metadata
}

func (s *Service) movieInfoForRef(ref ProviderRef) (*model.MovieInfo, error) {
	if !ref.IsMerged() {
		source := ref.Primary()
		return s.engine.GetMovieInfoByProviderID(sdkpid.ProviderID{
			Provider: source.Provider,
			ID:       source.ID,
		}, source.Update == nil || !*source.Update)
	}

	var movies []*model.MovieInfo
	for _, source := range ref.Sources {
		movie, err := s.engine.GetMovieInfoByProviderID(sdkpid.ProviderID{
			Provider: source.Provider,
			ID:       source.ID,
		}, source.Update == nil || !*source.Update)
		if err == nil {
			movies = append(movies, movie)
		}
	}
	if len(movies) == 0 {
		return nil, fmt.Errorf("all MetaTube merge sources failed")
	}
	return mergeMovieDetails(movies), nil
}

func (s *Service) searchResultToMetadata(r *http.Request, movie *model.MovieSearchResult, badge bool) Metadata {
	ref := SingleRef(movie.Provider, movie.ID, badge)
	ratingKey := EncodeRatingKey(ref)
	title := formatSearchTitle(movie)
	releaseDate := dateStringFromDate(movie.ReleaseDate)
	thumb := absoluteURL(r, s.settings, "images/movie/primary", ratingKey)
	return Metadata{
		RatingKey:             ratingKey,
		Key:                   prefixedPath(s.settings.PathPrefix(), metadataPath+"/"+ratingKey),
		GUID:                  s.guid(ratingKey),
		Type:                  "movie",
		Title:                 title,
		Summary:               title,
		OriginallyAvailableAt: releaseDate,
		Year:                  year(releaseDate),
		Thumb:                 thumb,
		Image:                 []Image{{Type: "coverPoster", URL: thumb, Alt: title}},
		Guid:                  sourceGuids(ref),
	}
}

func (s *Service) mergedSearchResultToMetadata(r *http.Request, movies []*model.MovieSearchResult, badge bool) Metadata {
	sources := make([]ProviderID, 0, len(movies))
	for _, movie := range movies {
		sources = append(sources, ProviderID{Provider: movie.Provider, ID: movie.ID})
	}
	ref := ProviderRef{Sources: sources, Badge: badge}.WithBadge(badge)
	ratingKey := EncodeRatingKey(ref)
	title := formatSearchTitle(movies[0])
	releaseDate := dateStringFromDate(movies[0].ReleaseDate)
	thumb := absoluteURL(r, s.settings, "images/movie/primary", ratingKey)
	providers := make([]string, 0, len(sources))
	for _, source := range sources {
		providers = append(providers, source.Provider)
	}
	return Metadata{
		RatingKey:             ratingKey,
		Key:                   prefixedPath(s.settings.PathPrefix(), metadataPath+"/"+ratingKey),
		GUID:                  s.guid(ratingKey),
		Type:                  "movie",
		Title:                 title,
		Summary:               "Merged from " + strings.Join(providers, ", "),
		OriginallyAvailableAt: releaseDate,
		Year:                  year(releaseDate),
		Thumb:                 thumb,
		Image:                 []Image{{Type: "coverPoster", URL: thumb, Alt: title}},
		Guid:                  sourceGuids(ref),
	}
}

func (s *Service) movieToMetadata(r *http.Request, movie *model.MovieInfo, ref ProviderRef, language string) Metadata {
	movie = s.applyPreferences(movie, language)
	ratingKey := EncodeRatingKey(ref)
	title := s.formatMovieTitle(movie)
	releaseDate := dateStringFromDate(movie.ReleaseDate)
	thumb := absoluteURL(r, s.settings, "images/movie/primary", ratingKey)
	art := absoluteURL(r, s.settings, "images/movie/backdrop", ratingKey)

	metadata := Metadata{
		RatingKey:             ratingKey,
		Key:                   prefixedPath(s.settings.PathPrefix(), metadataPath+"/"+ratingKey),
		GUID:                  s.guid(ratingKey),
		Type:                  "movie",
		Title:                 title,
		OriginalTitle:         movie.Title,
		Summary:               movie.Summary,
		Tagline:               ref.Legacy(),
		ContentRating:         defaultContentRating,
		OriginallyAvailableAt: releaseDate,
		Year:                  year(releaseDate),
		Thumb:                 thumb,
		Art:                   art,
		Image: []Image{
			{Type: "coverPoster", URL: thumb, Alt: title},
			{Type: "background", URL: art, Alt: title},
		},
		Guid:    sourceGuids(ref),
		Country: []Tag{{Tag: defaultCountry}},
		Genre:   toTags(uniqueStrings([]string(movie.Genres))),
	}
	if movie.Runtime > 0 {
		metadata.Duration = movie.Runtime * 60 * 1000
	}
	if movie.Maker != "" {
		metadata.Studio = movie.Maker
		metadata.StudioTag = []Tag{{Tag: movie.Maker}}
	}
	if s.settings.EnableDirectors && movie.Director != "" {
		metadata.Director = []Tag{{Tag: movie.Director}}
	}
	if actors := uniqueStrings([]string(movie.Actors)); len(actors) > 0 {
		metadata.Role = s.roles(r, actors)
	}
	if s.settings.EnableRatings && movie.Score > 0 {
		value := movie.Score * 2
		if value > 10 {
			value = 10
		}
		metadata.Rating = []PlexRating{{
			Image: "metatube://image.rating",
			Type:  "audience",
			Value: value,
		}}
	}
	return metadata
}

func (s *Service) roles(r *http.Request, actors []string) []Role {
	roles := make([]Role, 0, len(actors))
	for index, actor := range actors {
		role := Role{Tag: actor, Order: index + 1}
		if s.settings.EnableActorImages && s.hasActorImage(actor) {
			role.Thumb = absoluteURL(r, s.settings, "images/actor", gfriendsProvider, actor)
		}
		roles = append(roles, role)
	}
	return roles
}

func (s *Service) hasActorImage(name string) bool {
	results, err := s.engine.SearchActor(name, gfriendsProvider, false)
	if err != nil {
		return false
	}
	for _, actor := range results {
		if len(actor.Images) > 0 {
			return true
		}
	}
	return false
}

func (s *Service) applyPreferences(movie *model.MovieInfo, language string) *model.MovieInfo {
	applied := *movie
	applied.Actors = append([]string(nil), []string(movie.Actors)...)
	applied.Genres = append([]string(nil), []string(movie.Genres)...)
	applied.PreviewImages = append([]string(nil), []string(movie.PreviewImages)...)

	if s.settings.EnableRealActorNames && avbaseSupportedProviders[strings.ToUpper(applied.Provider)] {
		if results, err := s.engine.SearchMovie(applied.ID, avbaseProvider, true); err == nil && len(results) == 1 && len(results[0].Actors) > 0 {
			applied.Actors = append([]string(nil), []string(results[0].Actors)...)
		}
	}
	if s.settings.EnableTitleSubstitution && s.settings.TitleSubstitutionTable != "" {
		table := parseTable(s.settings.TitleSubstitutionTable, "\n", true, false)
		for old, replacement := range table {
			applied.Title = strings.ReplaceAll(applied.Title, old, replacement)
		}
	}
	if s.settings.EnableActorSubstitution && s.settings.ActorSubstitutionTable != "" {
		table := parseTable(s.settings.ActorSubstitutionTable, "\n", true, false)
		applied.Actors = tableSubstitute(table, []string(applied.Actors))
	}
	if s.settings.EnableGenreSubstitution && s.settings.GenreSubstitutionTable != "" {
		table := parseTable(s.settings.GenreSubstitutionTable, "\n", true, false)
		applied.Genres = tableSubstitute(table, []string(applied.Genres))
	}
	if language != "" {
		if s.settings.TranslationHas(translationTitle) && applied.Title != "" {
			applied.Title = s.translateText(applied.Title, language)
		}
		if s.settings.TranslationHas(translationSummary) && applied.Summary != "" {
			applied.Summary = s.translateText(applied.Summary, language)
		}
	}
	return &applied
}

func (s *Service) translateText(text string, language string) string {
	if text == "" || strings.HasPrefix(strings.ToLower(language), "ja") {
		return text
	}
	params := parseTable(s.settings.TranslationEngineParameters, ",", false, true)
	target := language
	if forced := params["to"]; forced != "" {
		target = forced
		delete(params, "to")
	}
	time.Sleep(time.Second)
	raw, err := json.Marshal(params)
	if err != nil {
		return text
	}
	unmarshal := func(v any) error {
		return json.Unmarshal(raw, v)
	}
	result, err := translate.New(s.settings.TranslationEngine, unmarshal).Translate(text, "auto", target)
	if err != nil || result == "" {
		return text
	}
	return result
}

func (s *Service) pidFromMatch(body map[string]any) (ProviderRef, bool) {
	if guid, ok := body["guid"].(string); ok {
		return ParseGUID(guid, s.settings.ProviderIdentifier)
	}
	if title, ok := body["title"].(string); ok {
		return ParseGUID(title, s.settings.ProviderIdentifier)
	}
	return ProviderRef{}, false
}

func (s *Service) queryFromMatch(body map[string]any) string {
	manual := intValue(body["manual"]) == 1
	if !manual {
		if filename, ok := body["filename"].(string); ok && filename != "" {
			return filenameStem(filename)
		}
	}
	if title, ok := body["title"].(string); ok && title != "" {
		return title
	}
	if filename, ok := body["filename"].(string); ok && filename != "" {
		return filenameStem(filename)
	}
	return ""
}

func (s *Service) guid(ratingKey string) string {
	return s.settings.ProviderIdentifier + "://movie/" + ratingKey
}

func (s *Service) filterMovieResults(movies []*model.MovieSearchResult, query string) []*model.MovieSearchResult {
	includeAVBase := false
	if s.settings.EnableMovieProviderFilter {
		providers := parseList(s.settings.MovieProviderFilter, ",")
		if len(providers) > 0 {
			order := map[string]int{}
			for index, provider := range providers {
				order[provider] = index
				if provider == avbaseProvider {
					includeAVBase = true
				}
			}
			var filtered []*model.MovieSearchResult
			for _, movie := range movies {
				if _, ok := order[strings.ToUpper(movie.Provider)]; ok {
					filtered = append(filtered, movie)
				}
			}
			sort.SliceStable(filtered, func(i, j int) bool {
				return order[strings.ToUpper(filtered[i].Provider)] < order[strings.ToUpper(filtered[j].Provider)]
			})
			movies = filtered
		}
	}
	if !includeAVBase {
		filtered := movies[:0]
		for _, movie := range movies {
			if strings.EqualFold(movie.Provider, avbaseProvider) {
				continue
			}
			filtered = append(filtered, movie)
		}
		movies = filtered
	}
	exact := exactMovieResults(movies, query)
	if len(exact) > 0 {
		return exact
	}
	return uniqueMovieResults(movies)
}

func exactMovieResults(movies []*model.MovieSearchResult, query string) []*model.MovieSearchResult {
	if !looksLikeCatalogNumber(query) {
		return nil
	}
	needle := normalizeCatalogNumber(query)
	var exact []*model.MovieSearchResult
	for _, movie := range movies {
		if needle == normalizeCatalogNumber(movie.Number) || needle == normalizeCatalogNumber(movie.ID) {
			exact = append(exact, movie)
		}
	}
	return uniqueMovieResults(exact)
}

func uniqueMovieResults(movies []*model.MovieSearchResult) []*model.MovieSearchResult {
	seen := map[string]bool{}
	var out []*model.MovieSearchResult
	for _, movie := range movies {
		key := strings.ToUpper(movie.Provider) + "\x00" + strings.ToUpper(movie.ID)
		if movie.Provider == "" || movie.ID == "" || seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, movie)
	}
	return out
}

func mergeMovieDetails(movies []*model.MovieInfo) *model.MovieInfo {
	merged := *movies[0]
	for _, movie := range movies[1:] {
		if !hasValue(merged.Title) && hasValue(movie.Title) {
			merged.Title = movie.Title
		}
		if !hasValue(merged.Number) && hasValue(movie.Number) {
			merged.Number = movie.Number
		}
		if !hasValue(merged.Homepage) && hasValue(movie.Homepage) {
			merged.Homepage = movie.Homepage
		}
		if !hasValue(merged.CoverURL) && hasValue(movie.CoverURL) {
			merged.CoverURL = movie.CoverURL
		}
		if !hasValue(merged.ThumbURL) && hasValue(movie.ThumbURL) {
			merged.ThumbURL = movie.ThumbURL
		}
		if !hasValue(merged.BigCoverURL) && hasValue(movie.BigCoverURL) {
			merged.BigCoverURL = movie.BigCoverURL
		}
		if !hasValue(merged.BigThumbURL) && hasValue(movie.BigThumbURL) {
			merged.BigThumbURL = movie.BigThumbURL
		}
		if !hasValue(merged.Summary) && hasValue(movie.Summary) {
			merged.Summary = movie.Summary
		}
		if !hasValue(merged.Director) && hasValue(movie.Director) {
			merged.Director = movie.Director
		}
		if !hasValue(merged.Maker) && hasValue(movie.Maker) {
			merged.Maker = movie.Maker
		}
		if !hasValue(merged.Label) && hasValue(movie.Label) {
			merged.Label = movie.Label
		}
		if !hasValue(merged.Series) && hasValue(movie.Series) {
			merged.Series = movie.Series
		}
		if merged.Runtime <= 0 && movie.Runtime > 0 {
			merged.Runtime = movie.Runtime
		}
		if merged.Score <= 0 && movie.Score > 0 {
			merged.Score = movie.Score
		}
		merged.Actors = uniqueStrings(append([]string(merged.Actors), []string(movie.Actors)...))
		merged.Genres = uniqueStrings(append([]string(merged.Genres), []string(movie.Genres)...))
		merged.PreviewImages = uniqueStrings(append([]string(merged.PreviewImages), []string(movie.PreviewImages)...))
	}
	return &merged
}

func formatSearchTitle(movie *model.MovieSearchResult) string {
	return strings.TrimSpace(strings.TrimSpace(movie.Number) + " " + strings.TrimSpace(movie.Title))
}

func (s *Service) formatMovieTitle(movie *model.MovieInfo) string {
	template := "{number} {title}"
	if s.settings.EnableTitleTemplate && s.settings.TitleTemplate != "" {
		template = s.settings.TitleTemplate
	}
	replacer := strings.NewReplacer(
		"{provider}", movie.Provider,
		"{id}", movie.ID,
		"{number}", movie.Number,
		"{title}", movie.Title,
		"{series}", movie.Series,
		"{maker}", movie.Maker,
		"{label}", movie.Label,
		"{director}", movie.Director,
		"{actors}", strings.Join([]string(movie.Actors), " "),
		"{first_actor}", firstString([]string(movie.Actors)),
		"{year}", fmt.Sprint(year(dateStringFromDate(movie.ReleaseDate))),
		"{date}", dateStringFromDate(movie.ReleaseDate),
	)
	title := strings.TrimSpace(replacer.Replace(template))
	if title == "" {
		return strings.TrimSpace(strings.TrimSpace(movie.Number) + " " + strings.TrimSpace(movie.Title))
	}
	return title
}

func sourceGuids(ref ProviderRef) []Guid {
	guids := make([]Guid, 0, len(ref.Sources))
	for _, source := range ref.Sources {
		guids = append(guids, Guid{ID: "metatube://" + source.Provider + "/" + url.PathEscape(source.ID)})
	}
	return guids
}

func toTags(values []string) []Tag {
	tags := make([]Tag, 0, len(values))
	for _, value := range values {
		tags = append(tags, Tag{Tag: value})
	}
	return tags
}

func intValue(value any) int {
	switch v := value.(type) {
	case int:
		return v
	case float64:
		return int(v)
	case string:
		if v == "" {
			return 0
		}
		if v == "true" {
			return 1
		}
	}
	return 0
}

func plexLanguage(r *http.Request) string {
	if value := r.Header.Get("X-Plex-Language"); value != "" {
		return value
	}
	return r.URL.Query().Get("X-Plex-Language")
}

func firstString(values []string) string {
	if len(values) == 0 {
		return ""
	}
	return values[0]
}
