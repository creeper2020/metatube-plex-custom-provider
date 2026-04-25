import unittest

from metatube_provider.config import Settings
from metatube_provider.server import request_path


class ServerTests(unittest.TestCase):
    def test_request_path_without_auth_accepts_root_paths(self):
        settings = Settings()

        self.assertEqual(request_path("/", settings), "/")
        self.assertEqual(request_path("/library/metadata/matches", settings), "/library/metadata/matches")

    def test_request_path_with_auth_rejects_missing_prefix(self):
        settings = Settings(auth_token="secret")

        self.assertIsNone(request_path("/", settings))
        self.assertIsNone(request_path("/library/metadata/matches", settings))

    def test_request_path_with_auth_strips_prefix(self):
        settings = Settings(auth_token="secret")

        self.assertEqual(request_path("/_metatube/secret", settings), "/")
        self.assertEqual(
            request_path("/_metatube/secret/library/metadata/matches", settings),
            "/library/metadata/matches",
        )


if __name__ == "__main__":
    unittest.main()
