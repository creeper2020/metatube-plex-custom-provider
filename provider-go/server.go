package main

import (
	"encoding/json"
	"image"
	"image/jpeg"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"strings"

	sdkpid "github.com/metatube-community/metatube-sdk-go/engine/providerid"
	"github.com/metatube-community/metatube-sdk-go/imageutil/badge"
)

type Server struct {
	settings Settings
	service  *Service
}

func NewServer(settings Settings, service *Service) *Server {
	return &Server{settings: settings, service: service}
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	reqPath, ok := requestPath(r.URL.Path, s.settings)
	if !ok {
		writeError(w, http.StatusNotFound, "not found")
		return
	}

	switch {
	case r.Method == http.MethodGet && (reqPath == "" || reqPath == "/"):
		writeJSON(w, http.StatusOK, s.service.Provider())
	case r.Method == http.MethodGet && reqPath == "/health":
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	case r.Method == http.MethodPost && reqPath == matchPath:
		s.handleMatch(w, r)
	case r.Method == http.MethodGet && strings.HasPrefix(reqPath, metadataPath+"/"):
		s.handleMetadata(w, r, strings.TrimPrefix(reqPath, metadataPath+"/"))
	case getOrHead(r) && strings.HasPrefix(reqPath, "/images/movie/primary/"):
		s.handleMovieImage(w, r, strings.TrimPrefix(reqPath, "/images/movie/primary/"), true)
	case getOrHead(r) && strings.HasPrefix(reqPath, "/images/movie/backdrop/"):
		s.handleMovieImage(w, r, strings.TrimPrefix(reqPath, "/images/movie/backdrop/"), false)
	case getOrHead(r) && strings.HasPrefix(reqPath, "/images/actor/"):
		s.handleActorImage(w, r, strings.TrimPrefix(reqPath, "/images/actor/"))
	default:
		writeError(w, http.StatusNotFound, "not found")
	}
}

func (s *Server) handleMatch(w http.ResponseWriter, r *http.Request) {
	defer r.Body.Close()
	var body map[string]any
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "request body is not valid JSON")
		return
	}
	response, err := s.service.Match(r, body)
	if err != nil {
		writeError(w, http.StatusBadGateway, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response)
}

func (s *Server) handleMetadata(w http.ResponseWriter, r *http.Request, suffix string) {
	if strings.HasSuffix(suffix, "/images") {
		ratingKey := strings.TrimSuffix(suffix, "/images")
		response, err := s.service.Images(r, ratingKey)
		if err != nil {
			writeError(w, http.StatusBadGateway, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, response)
		return
	}
	if strings.HasSuffix(suffix, "/children") || strings.HasSuffix(suffix, "/grandchildren") {
		writeJSON(w, http.StatusOK, Container(s.settings.ProviderIdentifier, nil))
		return
	}
	ratingKey, _, _ := strings.Cut(suffix, "/")
	response, err := s.service.Metadata(r, ratingKey)
	if err != nil {
		writeError(w, http.StatusBadGateway, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response)
}

func (s *Server) handleMovieImage(w http.ResponseWriter, r *http.Request, ratingKey string, primary bool) {
	ref, err := DecodeRatingKey(ratingKey)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	source := ref.Primary()
	pid := sdkpid.ProviderID{Provider: source.Provider, ID: source.ID}
	w.Header().Set("Content-Type", "image/jpeg")
	w.Header().Set("Cache-Control", "public, max-age=604800")
	if r.Method == http.MethodHead {
		w.WriteHeader(http.StatusOK)
		return
	}

	var img image.Image
	if primary {
		pos := -1.0
		if source.Position > 0 {
			pos = source.Position
		}
		img, err = s.service.engine.GetMoviePrimaryImage(pid, -1, pos)
	} else {
		img, err = s.service.engine.GetMovieBackdropImage(pid)
	}
	if err != nil {
		writeError(w, http.StatusBadGateway, err.Error())
		return
	}
	if ref.Badge && s.settings.EnableBadges {
		img, err = badge.Badge(img, s.settings.BadgeURL)
		if err != nil {
			writeError(w, http.StatusBadGateway, err.Error())
			return
		}
	}
	if err := jpeg.Encode(w, img, &jpeg.Options{Quality: 88}); err != nil {
		log.Printf("encode image error: %v", err)
	}
}

func (s *Server) handleActorImage(w http.ResponseWriter, r *http.Request, suffix string) {
	provider, id, ok := strings.Cut(suffix, "/")
	if !ok || provider == "" || id == "" {
		writeError(w, http.StatusBadRequest, "invalid actor image path")
		return
	}
	provider, _ = url.PathUnescape(provider)
	id, _ = url.PathUnescape(id)
	pid := sdkpid.ProviderID{Provider: provider, ID: id}
	w.Header().Set("Content-Type", "image/jpeg")
	w.Header().Set("Cache-Control", "public, max-age=604800")
	if r.Method == http.MethodHead {
		w.WriteHeader(http.StatusOK)
		return
	}

	img, err := s.service.engine.GetActorPrimaryImage(pid)
	if err != nil {
		writeError(w, http.StatusBadGateway, err.Error())
		return
	}
	if err := jpeg.Encode(w, img, &jpeg.Options{Quality: 88}); err != nil {
		log.Printf("encode actor image error: %v", err)
	}
}

func getOrHead(r *http.Request) bool {
	return r.Method == http.MethodGet || r.Method == http.MethodHead
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	raw, err := json.Marshal(value)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Content-Length", strconv.Itoa(len(raw)))
	w.WriteHeader(status)
	_, _ = w.Write(raw)
}

func writeError(w http.ResponseWriter, status int, message string) {
	raw, _ := json.Marshal(map[string]string{
		"error":   http.StatusText(status),
		"message": message,
	})
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_, _ = w.Write(raw)
}
