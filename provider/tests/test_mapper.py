import unittest

from metatube_provider.config import Settings
from metatube_provider.mapper import MetadataMapper
from metatube_provider.provider_id import MergedProviderID, ProviderID


class FakeAPI:
    def primary_image_url(self, provider, id, **params):
        return f"https://images.example/{provider}/{id}/poster"

    def backdrop_image_url(self, provider, id, **params):
        return f"https://images.example/{provider}/{id}/art"


class MapperTests(unittest.TestCase):
    def test_movie_metadata_shape(self):
        settings = Settings(enable_actor_images=False)
        mapper = MetadataMapper(settings, FakeAPI())
        movie = {
            "id": "ABC-123",
            "provider": "FANZA",
            "number": "ABC-123",
            "title": "Example Movie",
            "summary": "Example summary",
            "release_date": "2026-01-02",
            "runtime": 120,
            "score": 4.5,
            "director": "Example Director",
            "maker": "Example Studio",
            "genres": ["Drama", "Drama", "Action"],
            "actors": ["Actor A", "Actor A", "Actor B"],
        }

        metadata = mapper.movie_to_metadata(movie, ProviderID("FANZA", "ABC-123"), "en-US")

        self.assertEqual(metadata["type"], "movie")
        self.assertEqual(metadata["title"], "ABC-123 Example Movie")
        self.assertEqual(metadata["originallyAvailableAt"], "2026-01-02")
        self.assertEqual(metadata["year"], 2026)
        self.assertEqual(metadata["duration"], 120 * 60 * 1000)
        self.assertEqual(metadata["Director"], [{"tag": "Example Director"}])
        self.assertEqual(metadata["Studio"], [{"tag": "Example Studio"}])
        self.assertEqual(metadata["Genre"], [{"tag": "Drama"}, {"tag": "Action"}])
        self.assertEqual(metadata["Role"], [{"tag": "Actor A", "order": 1}, {"tag": "Actor B", "order": 2}])
        self.assertEqual(metadata["Rating"][0]["value"], 9.0)

    def test_movie_metadata_key_uses_path_prefix(self):
        settings = Settings(enable_actor_images=False, auth_token="secret")
        mapper = MetadataMapper(settings, FakeAPI())
        movie = {
            "id": "ABC-123",
            "provider": "FANZA",
            "number": "ABC-123",
            "title": "Example Movie",
            "release_date": "2026-01-02",
            "genres": [],
            "actors": [],
        }

        metadata = mapper.movie_to_metadata(movie, ProviderID("FANZA", "ABC-123"), "en-US")

        self.assertTrue(metadata["key"].startswith("/_metatube/secret/library/metadata/"))

    def test_merged_movie_metadata_uses_primary_images_and_all_source_guids(self):
        settings = Settings(enable_actor_images=False)
        mapper = MetadataMapper(settings, FakeAPI())
        movie = {
            "id": "JUQ-907",
            "provider": "JavBus",
            "number": "JUQ-907",
            "title": "Example Movie",
            "release_date": "2024-10-04",
            "runtime": 120,
            "score": 3.5,
            "genres": ["Drama"],
            "actors": ["Actor A"],
        }
        pid = MergedProviderID(
            sources=(
                ProviderID("JavBus", "JUQ-907"),
                ProviderID("JAV321", "juq00907"),
            )
        )

        metadata = mapper.movie_to_metadata(movie, pid, "en-US")

        self.assertIn("mt_", metadata["ratingKey"])
        self.assertEqual(metadata["thumb"], "https://images.example/JavBus/JUQ-907/poster")
        self.assertEqual(
            metadata["Guid"],
            [
                {"id": "metatube://JavBus/JUQ-907"},
                {"id": "metatube://JAV321/juq00907"},
            ],
        )

    def test_movie_metadata_ignores_invalid_runtime(self):
        settings = Settings(enable_actor_images=False)
        mapper = MetadataMapper(settings, FakeAPI())
        movie = {
            "id": "ABC-123",
            "provider": "FANZA",
            "number": "ABC-123",
            "title": "Example Movie",
            "release_date": "2026-01-02",
            "runtime": "unknown",
            "genres": [],
            "actors": [],
        }

        metadata = mapper.movie_to_metadata(movie, ProviderID("FANZA", "ABC-123"), "en-US")

        self.assertNotIn("duration", metadata)

    def test_search_result_requires_provider_and_id(self):
        settings = Settings(enable_actor_images=False)
        mapper = MetadataMapper(settings, FakeAPI())

        with self.assertRaises(ValueError):
            mapper.search_result_to_metadata({"provider": "FANZA", "title": "Broken"})


if __name__ == "__main__":
    unittest.main()
