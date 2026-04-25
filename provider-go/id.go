package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/url"
	"strings"
)

const ratingKeyPrefix = "mt_"

type ProviderID struct {
	Provider string  `json:"p"`
	ID       string  `json:"i"`
	Position float64 `json:"o,omitempty"`
	Update   *bool   `json:"u,omitempty"`
	Badge    bool    `json:"b,omitempty"`
}

type ProviderRef struct {
	Sources []ProviderID
	Badge   bool
}

func SingleRef(provider, id string, badge bool) ProviderRef {
	return ProviderRef{Sources: []ProviderID{{Provider: provider, ID: id, Badge: badge}}, Badge: badge}
}

func (r ProviderRef) Primary() ProviderID {
	return r.Sources[0]
}

func (r ProviderRef) IsMerged() bool {
	return len(r.Sources) > 1
}

func (r ProviderRef) Legacy() string {
	values := make([]string, 0, len(r.Sources))
	for _, source := range r.Sources {
		item := source.Provider + ":" + url.QueryEscape(source.ID)
		if source.Position > 0 {
			item += fmt.Sprintf(":%.2f", source.Position)
		}
		values = append(values, item)
	}
	if len(values) == 1 {
		return values[0]
	}
	return "merge:" + strings.Join(values, ",")
}

func (r ProviderRef) WithBadge(badge bool) ProviderRef {
	r.Badge = badge
	for i := range r.Sources {
		r.Sources[i].Badge = badge
	}
	return r
}

func EncodeRatingKey(ref ProviderRef) string {
	var payload map[string]any
	if ref.IsMerged() {
		sources := make([]map[string]any, 0, len(ref.Sources))
		for _, source := range ref.Sources {
			sources = append(sources, sourcePayload(source))
		}
		payload = map[string]any{"m": sources}
	} else {
		payload = sourcePayload(ref.Primary())
	}
	if ref.Badge {
		payload["b"] = true
	}
	raw, _ := json.Marshal(payload)
	return ratingKeyPrefix + strings.TrimRight(base64.URLEncoding.EncodeToString(raw), "=")
}

func DecodeRatingKey(value string) (ProviderRef, error) {
	if !strings.HasPrefix(value, ratingKeyPrefix) {
		return ProviderRef{}, fmt.Errorf("invalid MetaTube ratingKey: %s", value)
	}
	encoded := strings.TrimPrefix(value, ratingKeyPrefix)
	if m := len(encoded) % 4; m != 0 {
		encoded += strings.Repeat("=", 4-m)
	}
	raw, err := base64.URLEncoding.DecodeString(encoded)
	if err != nil {
		return ProviderRef{}, err
	}
	var payload map[string]json.RawMessage
	if err := json.Unmarshal(raw, &payload); err != nil {
		return ProviderRef{}, err
	}
	if merged, ok := payload["m"]; ok {
		var sources []ProviderID
		if err := json.Unmarshal(merged, &sources); err != nil {
			return ProviderRef{}, err
		}
		if len(sources) == 0 {
			return ProviderRef{}, fmt.Errorf("empty merged ratingKey")
		}
		return ProviderRef{Sources: sources, Badge: rawBool(payload["b"])}, nil
	}
	var source ProviderID
	if err := json.Unmarshal(raw, &source); err != nil {
		return ProviderRef{}, err
	}
	if source.Provider == "" || source.ID == "" {
		return ProviderRef{}, fmt.Errorf("invalid MetaTube ratingKey payload")
	}
	source.Badge = rawBool(payload["b"])
	return ProviderRef{Sources: []ProviderID{source}, Badge: source.Badge}, nil
}

func ParseGUID(guid, providerIdentifier string) (ProviderRef, bool) {
	prefix := providerIdentifier + "://movie/"
	if strings.HasPrefix(guid, prefix) {
		ref, err := DecodeRatingKey(strings.TrimPrefix(guid, prefix))
		return ref, err == nil
	}
	if strings.HasPrefix(guid, "metatube://") {
		parts := strings.SplitN(strings.TrimPrefix(guid, "metatube://"), "/", 2)
		if len(parts) == 2 && parts[0] != "" && parts[1] != "" {
			id, _ := url.PathUnescape(parts[1])
			return SingleRef(parts[0], id, false), true
		}
	}
	if provider, id, found := strings.Cut(guid, ":"); found && provider != "" && id != "" {
		decoded, _ := url.QueryUnescape(id)
		return SingleRef(provider, decoded, false), true
	}
	return ProviderRef{}, false
}

func sourcePayload(source ProviderID) map[string]any {
	payload := map[string]any{"p": source.Provider, "i": source.ID}
	if source.Position > 0 {
		payload["o"] = source.Position
	}
	if source.Update != nil {
		payload["u"] = *source.Update
	}
	return payload
}

func rawBool(raw json.RawMessage) bool {
	var value bool
	return len(raw) > 0 && json.Unmarshal(raw, &value) == nil && value
}
