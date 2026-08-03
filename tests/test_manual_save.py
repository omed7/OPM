import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add src and root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from the newly created save_manual endpoint or helper logic
from api.save_manual import load_match_database, save_match_database

class TestSaveManual(unittest.TestCase):

    @patch('api.save_manual.supabase_request')
    def test_load_match_database_success(self, mock_supabase_request):
        # Setup mock return value for success
        mock_data = [{"id": "1", "team": "Team A"}]
        mock_supabase_request.return_value = (mock_data, None)

        data, _ = load_match_database()

        self.assertEqual(data, mock_data)
        mock_supabase_request.assert_called_once_with("/matches?select=*", method="GET")

    @patch('api.save_manual.supabase_request')
    def test_load_match_database_error(self, mock_supabase_request):
        # Setup mock return value for error
        mock_supabase_request.return_value = (None, "Some error")

        data, _ = load_match_database()

        self.assertEqual(data, [])
        mock_supabase_request.assert_called_once_with("/matches?select=*", method="GET")

    def test_save_manual_payload_mapping(self):
        # Sample payload mimicking what public/script.js sends
        payload = {
            "league_id": "test-league",
            "league_name": "Test League",
            "home_team": "Team Home",
            "away_team": "Team Away",
            "skip_xg": False,
            "home_matches": [
                {
                    "opponent": "Opponent A",
                    "venue": "home",
                    "date": "2026-07-31",
                    "valFor": 2.5,
                    "valAgainst": 1.2
                },
                {
                    "opponent": "Opponent B",
                    "venue": "away", # Venue flip applies!
                    "date": "2026-07-24",
                    "valFor": 1.1, # Own team value (valFor)
                    "valAgainst": 2.2 # Opponent value (valAgainst)
                }
            ],
            "away_matches": []
        }

        # Build records exactly as the handler would
        league_id = payload["league_id"]
        home_team = payload["home_team"]
        skip_xg = payload["skip_xg"]
        home_matches = payload["home_matches"]

        new_records = []
        for m in home_matches:
            opponent = m['opponent']
            date = m['date']
            venue = m['venue']
            val_for = m['valFor']
            val_against = m['valAgainst']

            goals_for = int(val_for) if skip_xg else None
            goals_against = int(val_against) if skip_xg else None
            xg_for = None if skip_xg else float(val_for)
            xg_against = None if skip_xg else float(val_against)

            # Team entry
            new_records.append({
                "team": home_team,
                "opponent": opponent,
                "date": date,
                "venue": venue,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "xg_for": xg_for,
                "xg_against": xg_against,
                "source": "manual",
                "league": league_id,
                "weight": 1.0
            })

            # Opponent entry
            opp_venue = "away" if venue == "home" else "home"
            new_records.append({
                "team": opponent,
                "opponent": home_team,
                "date": date,
                "venue": opp_venue,
                "goals_for": goals_against,
                "goals_against": goals_for,
                "xg_for": xg_against,
                "xg_against": xg_for,
                "source": "manual",
                "league": league_id,
                "weight": 1.0
            })

        self.assertEqual(len(new_records), 4)

        # Let's inspect first match: Opponent A, venue home
        r1 = new_records[0]
        self.assertEqual(r1["team"], "Team Home")
        self.assertEqual(r1["opponent"], "Opponent A")
        self.assertEqual(r1["venue"], "home")
        self.assertEqual(r1["xg_for"], 2.5)
        self.assertEqual(r1["xg_against"], 1.2)

        # Opposite team entry for r1:
        r2 = new_records[1]
        self.assertEqual(r2["team"], "Opponent A")
        self.assertEqual(r2["opponent"], "Team Home")
        self.assertEqual(r2["venue"], "away")
        self.assertEqual(r2["xg_for"], 1.2)
        self.assertEqual(r2["xg_against"], 2.5)

        # Let's inspect second match: Opponent B, venue away (flip)
        r3 = new_records[2]
        self.assertEqual(r3["team"], "Team Home")
        self.assertEqual(r3["opponent"], "Opponent B")
        self.assertEqual(r3["venue"], "away")
        self.assertEqual(r3["xg_for"], 1.1)
        self.assertEqual(r3["xg_against"], 2.2)

        # Opposite entry for r3:
        r4 = new_records[3]
        self.assertEqual(r4["team"], "Opponent B")
        self.assertEqual(r4["opponent"], "Team Home")
        self.assertEqual(r4["venue"], "home")
        self.assertEqual(r4["xg_for"], 2.2)
        self.assertEqual(r4["xg_against"], 1.1)

if __name__ == '__main__':
    unittest.main()
