import json
import unittest

from src.validate_public_data import validate_payload


class TestPublicDataKickoffTimeValidation(unittest.TestCase):
    def payload_with_time(self, kickoff_time):
        return {
            "meta": {"version": "test", "generated_at": "2026-08-16T00:00:00Z"},
            "leagues": [
                {
                    "id": "premier_league",
                    "name": "Premier League",
                    "metric": "xg",
                    "fixtures": [
                        {
                            "home_team": "Home FC",
                            "away_team": "Away FC",
                            "date": "2026-08-16",
                            "kickoff_time": kickoff_time,
                        }
                    ],
                }
            ],
        }

    def test_accepts_optional_hh_mm_source_kickoff_time(self):
        payload = self.payload_with_time("21:30")

        self.assertEqual(validate_payload(payload, json.dumps(payload)), (1, 1))

    def test_rejects_invalid_source_kickoff_time(self):
        payload = self.payload_with_time("25:30")

        with self.assertRaisesRegex(ValueError, "kickoff_time"):
            validate_payload(payload, json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
