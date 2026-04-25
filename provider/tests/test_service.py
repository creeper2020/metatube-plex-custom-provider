import unittest

from metatube_provider.config import Settings
from metatube_provider.provider_id import MergedProviderID, decode_rating_key
from metatube_provider.service import ProviderService, merge_movie_details


class ServiceTests(unittest.TestCase):
    def test_filter_movies_keeps_exact_catalog_matches(self):
        service = ProviderService(Settings())
        movies = [
            {"provider": "JavBus", "id": "IPX-333", "number": "IPX-333"},
            {"provider": "JAV321", "id": "ipx00333", "number": "IPX-333"},
            {"provider": "DUGA", "id": "peters-2063", "number": "PYM-462"},
        ]

        filtered = service.filter_movies(movies, query="ipx-333")

        self.assertEqual([movie["provider"] for movie in filtered], ["JavBus", "JAV321"])

    def test_filter_movies_deduplicates_exact_catalog_matches(self):
        service = ProviderService(Settings())
        movies = [
            {"provider": "JavBus", "id": "IPX-333", "number": "IPX-333"},
            {"provider": "JavBus", "id": "IPX-333", "number": "IPX-333"},
            {"provider": "JAV321", "id": "ipx00333", "number": "IPX-333"},
        ]

        filtered = service.filter_movies(movies, query="ipx-333")

        self.assertEqual([(movie["provider"], movie["id"]) for movie in filtered], [
            ("JavBus", "IPX-333"),
            ("JAV321", "ipx00333"),
        ])

    def test_filter_movies_keeps_backend_order_when_query_is_not_catalog_number(self):
        service = ProviderService(Settings())
        movies = [
            {"provider": "A", "id": "1", "number": "ONE"},
            {"provider": "B", "id": "2", "number": "TWO"},
        ]

        self.assertEqual(service.filter_movies(movies, query="some title"), movies)

    def test_match_metadata_puts_merged_candidate_first_for_exact_catalog_matches(self):
        service = ProviderService(Settings())
        movies = [
            {"provider": "JavBus", "id": "JUQ-907", "number": "JUQ-907", "title": "Title"},
            {"provider": "JAV321", "id": "juq00907", "number": "JUQ-907", "title": "Title"},
        ]

        metadata = service.match_metadata(movies, query="JUQ-907", badge=False, manual=True)
        decoded = decode_rating_key(metadata[0]["ratingKey"])

        self.assertIsInstance(decoded, MergedProviderID)
        self.assertEqual([item["id"] for item in metadata[0]["Guid"]], [
            "metatube://JavBus/JUQ-907",
            "metatube://JAV321/juq00907",
        ])
        self.assertEqual(len(metadata), 3)

    def test_merge_movie_details_fills_missing_data_from_secondary_sources(self):
        merged = merge_movie_details([
            {
                "provider": "JavBus",
                "id": "JUQ-907",
                "number": "JUQ-907",
                "title": "Title",
                "score": 0,
                "runtime": 120,
                "actors": [],
                "genres": ["Drama"],
                "maker": "Primary Studio",
            },
            {
                "provider": "JAV321",
                "id": "juq00907",
                "number": "JUQ-907",
                "title": "Title",
                "score": 3.5,
                "runtime": 120,
                "actors": ["Actor A"],
                "genres": ["Drama", "Action"],
                "maker": "Secondary Studio",
            },
        ])

        self.assertEqual(merged["maker"], "Primary Studio")
        self.assertEqual(merged["score"], 3.5)
        self.assertEqual(merged["actors"], ["Actor A"])
        self.assertEqual(merged["genres"], ["Drama", "Action"])


if __name__ == "__main__":
    unittest.main()
