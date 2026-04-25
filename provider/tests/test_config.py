import os
import tempfile
import unittest
from pathlib import Path

from metatube_provider.config import Settings, load_env_file


class ConfigTests(unittest.TestCase):
    def test_path_prefix_is_empty_without_auth_token(self):
        self.assertEqual(Settings().path_prefix, "")

    def test_path_prefix_uses_auth_path_and_token(self):
        settings = Settings(auth_path="_private", auth_token="abc123")

        self.assertEqual(settings.path_prefix, "/_private/abc123")

    def test_load_env_file_does_not_override_existing_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "METATUBE_TEST_VALUE=from-file\n"
                "METATUBE_TEST_EXISTING=from-file\n",
                encoding="utf-8",
            )

            old_value = os.environ.get("METATUBE_TEST_EXISTING")
            os.environ["METATUBE_TEST_EXISTING"] = "from-env"
            os.environ.pop("METATUBE_TEST_VALUE", None)
            try:
                load_env_file(str(env_file))

                self.assertEqual(os.environ["METATUBE_TEST_VALUE"], "from-file")
                self.assertEqual(os.environ["METATUBE_TEST_EXISTING"], "from-env")
            finally:
                os.environ.pop("METATUBE_TEST_VALUE", None)
                if old_value is None:
                    os.environ.pop("METATUBE_TEST_EXISTING", None)
                else:
                    os.environ["METATUBE_TEST_EXISTING"] = old_value


if __name__ == "__main__":
    unittest.main()
