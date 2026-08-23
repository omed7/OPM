import json
import unittest

from src.validate_public_data import validate_payload


class TestPublicDataKickoffTimeValidation(unittest.TestCase):
    def payload_with_time(self, kickoff_time, kickoff_at=None, status=None):
        fixture = {
            "home_team": "Home FC",
            "away_team": "Away FC",
            "date": "2026-08-16",
            "kickoff_time": kickoff_time,
        }
        if kickoff_at is not None:
            fixture["kickoff_at"] = kickoff_at
        if status is not None:
            fixture["status"] = status
        return {
            "meta": {"version": "test", "generated_at": "2026-08-16T00:00:00Z"},
            "leagues": [{
                "id": "premier_league",
                "name": "Premier League",
                "metric": "xg",
                "fixtures": [fixture],
            }],
        }

    def test_accepts_optional_hh_mm_source_kickoff_time(self):
        payload = self.payload_with_time("21:30")

        self.assertEqual(validate_payload(payload, json.dumps(payload)), (1, 1))

    def test_rejects_invalid_source_kickoff_time(self):
        payload = self.payload_with_time("25:30")

        with self.assertRaisesRegex(ValueError, "kickoff_time"):
            validate_payload(payload, json.dumps(payload))

    def test_accepts_optional_completed_fixture_utc_timestamp(self):
        payload = self.payload_with_time(
            "21:30", kickoff_at="2026-08-16T18:30:00Z", status="FINISHED"
        )

        self.assertEqual(validate_payload(payload, json.dumps(payload)), (1, 1))

    def test_rejects_noncanonical_or_nonfinished_fixture_timestamp(self):
        invalid_values = [
            ("2026-08-16T18:30:00+00:00", "FINISHED"),
            ("2026-08-16 18:30:00Z", "FINISHED"),
            ("2026-08-16T18:30:00Z", None),
        ]
        for kickoff_at, status in invalid_values:
            with self.subTest(kickoff_at=kickoff_at, status=status):
                payload = self.payload_with_time("21:30", kickoff_at=kickoff_at, status=status)
                with self.assertRaisesRegex(ValueError, "kickoff_at"):
                    validate_payload(payload, json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
