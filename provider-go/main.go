package main

import (
	"log"
	"net"
	"net/http"

	"github.com/metatube-community/metatube-sdk-go/database"
	"github.com/metatube-community/metatube-sdk-go/engine"
	_ "github.com/metatube-community/metatube-sdk-go/provider/avbase"
	_ "github.com/metatube-community/metatube-sdk-go/translate/baidu"
	_ "github.com/metatube-community/metatube-sdk-go/translate/deepl"
	_ "github.com/metatube-community/metatube-sdk-go/translate/google"
	_ "github.com/metatube-community/metatube-sdk-go/translate/googlefree"
	_ "github.com/metatube-community/metatube-sdk-go/translate/openai"
)

func main() {
	settings := LoadSettings()

	db, err := database.Open(&database.Config{
		DSN:                  settings.DSN,
		PreparedStmt:         true,
		DisableAutomaticPing: true,
	})
	if err != nil {
		log.Fatal(err)
	}

	eng := engine.New(
		db,
		engine.WithEngineName("metatube-plex-provider"),
		engine.WithRequestTimeout(settings.RequestTimeout),
	)
	if err := eng.DBAutoMigrate(true); err != nil {
		log.Fatal(err)
	}

	addr := net.JoinHostPort(settings.Host, settings.Port)
	log.Printf("MetaTube Plex provider listening on http://%s", addr)
	if err := http.ListenAndServe(addr, NewServer(settings, NewService(settings, eng))); err != nil {
		log.Fatal(err)
	}
}
