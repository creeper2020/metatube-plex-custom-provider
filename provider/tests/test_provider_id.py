import unittest

from metatube_provider.provider_id import MergedProviderID, ProviderID, decode_rating_key, encode_rating_key, parse_guid


class ProviderIDTests(unittest.TestCase):
    def test_rating_key_round_trip(self):
        pid = ProviderID(provider="FANZA", id="ABC-123", position=0.25, update=True, badge=True)

        rating_key = encode_rating_key(pid)
        decoded = decode_rating_key(rating_key)

        self.assertRegex(rating_key, r"^[a-zA-Z0-9_-]+$")
        self.assertEqual(decoded, pid)

    def test_legacy_id_round_trip(self):
        pid = ProviderID.parse_legacy("FANZA:ABC-123:0.5:1")

        self.assertEqual(pid.provider, "FANZA")
        self.assertEqual(pid.id, "ABC-123")
        self.assertEqual(pid.position, 0.5)
        self.assertTrue(pid.update)
        self.assertEqual(pid.legacy(), "FANZA:ABC-123:0.5:1")

    def test_parse_provider_guid(self):
        identifier = "tv.plex.agents.custom.metatube.movie"
        pid = ProviderID(provider="FANZA", id="ABC-123")
        rating_key = encode_rating_key(pid)

        parsed = parse_guid(f"{identifier}://movie/{rating_key}", identifier)

        self.assertEqual(parsed, pid)

    def test_merged_rating_key_round_trip(self):
        pid = MergedProviderID(
            sources=(
                ProviderID(provider="JavBus", id="JUQ-907"),
                ProviderID(provider="JAV321", id="juq00907"),
            ),
            badge=True,
        )

        rating_key = encode_rating_key(pid)
        decoded = decode_rating_key(rating_key)

        self.assertRegex(rating_key, r"^[a-zA-Z0-9_-]+$")
        self.assertEqual(decoded, pid)
        self.assertEqual(decoded.primary.provider, "JavBus")


if __name__ == "__main__":
    unittest.main()
