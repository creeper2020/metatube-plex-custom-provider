package main

import (
	"encoding/base64"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"gorm.io/datatypes"
)

var catalogNumberPattern = regexp.MustCompile(`[A-Za-z]+[-_ ]?\d+`)

var subtitlePattern = regexp.MustCompile(`(?i)\.(ch[ist]|zho?(-(cn|hk|sg|tw))?)\.(ass|srt|ssa|smi|sub|idx|psb|vtt)$`)

var videoExtensions = map[string]bool{
	".3g2": true, ".3gp": true, ".asf": true, ".asx": true, ".avc": true,
	".avi": true, ".avs": true, ".bivx": true, ".bup": true, ".divx": true,
	".dv": true, ".dvr-ms": true, ".evo": true, ".fli": true, ".flv": true,
	".m2t": true, ".m2ts": true, ".m2v": true, ".m4v": true, ".mkv": true,
	".mov": true, ".mp4": true, ".mpeg": true, ".mpg": true, ".mts": true,
	".nsv": true, ".nuv": true, ".ogm": true, ".ogv": true, ".tp": true,
	".pva": true, ".qt": true, ".rm": true, ".rmvb": true, ".sdp": true,
	".svq3": true, ".strm": true, ".ts": true, ".ty": true, ".vdr": true,
	".viv": true, ".vob": true, ".vp3": true, ".wmv": true, ".wpl": true,
	".wtv": true, ".xsp": true, ".xvid": true, ".webm": true,
}

func filenameStem(value string) string {
	if value == "" {
		return ""
	}
	base := filepath.Base(value)
	ext := filepath.Ext(base)
	return strings.TrimSuffix(base, ext)
}

func normalizeCatalogNumber(value string) string {
	var b strings.Builder
	for _, r := range strings.ToUpper(value) {
		if (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') {
			b.WriteRune(r)
		}
	}
	return b.String()
}

func looksLikeCatalogNumber(value string) bool {
	value = strings.TrimSpace(value)
	return len(normalizeCatalogNumber(value)) >= 4 && catalogNumberPattern.MatchString(value)
}

func dateString(value string) string {
	if len(value) >= 10 {
		value = value[:10]
	}
	if parsed, err := time.Parse("2006-01-02", value); err == nil && parsed.Year() >= 1900 {
		return parsed.Format("2006-01-02")
	}
	return "1900-01-01"
}

func dateStringFromDate(value datatypes.Date) string {
	parsed := time.Time(value)
	if parsed.IsZero() || parsed.Year() < 1900 {
		return "1900-01-01"
	}
	return parsed.Format("2006-01-02")
}

func year(value string) int {
	if len(value) >= 4 {
		if parsed, err := strconv.Atoi(value[:4]); err == nil && parsed >= 1900 {
			return parsed
		}
	}
	return 0
}

func uniqueStrings(values []string) []string {
	seen := map[string]bool{}
	var out []string
	for _, value := range values {
		item := strings.TrimSpace(value)
		if item == "" || seen[item] {
			continue
		}
		seen[item] = true
		out = append(out, item)
	}
	return out
}

func hasValue(value string) bool {
	return strings.TrimSpace(value) != ""
}

func parseList(value string, sep string) []string {
	if sep == "" {
		sep = ","
	}
	var out []string
	for _, item := range strings.Split(value, sep) {
		item = strings.ToUpper(strings.TrimSpace(item))
		if item != "" {
			out = append(out, item)
		}
	}
	return out
}

func parseTable(value string, sep string, b64 bool, originKey bool) map[string]string {
	table := map[string]string{}
	if value == "" {
		return table
	}
	if b64 {
		raw, err := base64.StdEncoding.DecodeString(value)
		if err != nil {
			return table
		}
		value = string(raw)
	}
	if sep == "" {
		sep = ","
	}
	for _, item := range strings.Split(value, sep) {
		item = strings.TrimSpace(item)
		key, replacement, ok := strings.Cut(item, "=")
		if !ok || key == "" {
			continue
		}
		if !originKey {
			key = strings.ToUpper(key)
		}
		table[key] = replacement
	}
	return table
}

func tableSubstitute(table map[string]string, values []string) []string {
	out := make([]string, 0, len(values))
	for _, value := range values {
		if replacement, ok := table[strings.ToUpper(value)]; ok {
			out = append(out, replacement)
		} else {
			out = append(out, value)
		}
	}
	return out
}

func hasChineseSubtitle(videoName string) bool {
	return hasEmbeddedChineseSubtitle(videoName) || hasExternalChineseSubtitle(videoName)
}

func hasEmbeddedChineseSubtitle(videoName string) bool {
	base := filepath.Base(videoName)
	ext := strings.ToLower(filepath.Ext(base))
	if !videoExtensions[ext] {
		return false
	}
	name := strings.TrimSuffix(base, ext)
	if strings.Contains(name, "中文字幕") {
		return true
	}
	for _, part := range regexp.MustCompile(`[-_\s]`).Split(name, -1) {
		switch strings.ToUpper(part) {
		case "C", "UC", "CH":
			return true
		}
	}
	return false
}

func hasExternalChineseSubtitle(videoName string) bool {
	if videoName == "" {
		return false
	}
	base := filepath.Base(videoName)
	ext := strings.ToLower(filepath.Ext(base))
	if !videoExtensions[ext] {
		return false
	}
	stem := strings.TrimSuffix(base, ext)
	names, err := os.ReadDir(filepath.Dir(videoName))
	if err != nil {
		return false
	}
	for _, entry := range names {
		name := entry.Name()
		if subtitlePattern.MatchString(name) && strings.EqualFold(subtitlePattern.ReplaceAllString(name, ""), stem) {
			return true
		}
	}
	return false
}
