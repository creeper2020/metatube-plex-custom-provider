import unittest

from metatube_provider.config import Settings
from metatube_provider.plex import provider_response


class ProviderResponseTests(unittest.TestCase):
    def test_movie_provider_shape(self):
        settings = Settings()

        body = provider_response(settings.provider_identifier, settings.provider_title)
        provider = body["MediaProvider"]

        self.assertEqual(provider["identifier"], "tv.plex.agents.custom.metatube.movie")
        self.assertEqual(provider["Types"][0]["type"], 1)
        self.assertEqual(provider["Types"][0]["Scheme"][0]["scheme"], provider["identifier"])
        self.assertEqual(provider["Feature"][0], {"type": "metadata", "key": "/library/metadata"})
        self.assertEqual(provider["Feature"][1], {"type": "match", "key": "/library/metadata/matches"})

    def test_movie_provider_shape_with_path_prefix(self):
        settings = Settings(auth_token="secret")

        body = provider_response(settings.provider_identifier, settings.provider_title, settings.path_prefix)
        provider = body["MediaProvider"]

        self.assertEqual(provider["Feature"][0], {"type": "metadata", "key": "/_metatube/secret/library/metadata"})
        self.assertEqual(provider["Feature"][1], {"type": "match", "key": "/_metatube/secret/library/metadata/matches"})


if __name__ == "__main__":
    unittest.main()
