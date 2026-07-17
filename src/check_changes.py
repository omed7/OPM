import json
import sys

def main():
    if len(sys.argv) != 3:
        print("Usage: python check_changes.py <old_json> <new_json>")
        sys.exit(1)

    old_path = sys.argv[1]
    new_path = sys.argv[2]

    try:
        with open(old_path, 'r') as f1, open(new_path, 'r') as f2:
            old_data = json.load(f1)
            new_data = json.load(f2)

            # Check if old data has 'fixtures' (old schema) while new data has 'leagues' (new schema)
            if 'fixtures' in old_data and 'leagues' in new_data:
                sys.exit(1) # Schema changed, so data changed

            # Both should now be on 'leagues' schema, compare only the leagues
            if old_data.get('leagues') == new_data.get('leagues'):
                # No significant change
                sys.exit(0)
            else:
                # Changed
                sys.exit(1)
    except FileNotFoundError:
        # If the old file doesn't exist, it's a change
        sys.exit(1)
    except Exception as e:
        print(f"Error comparing files: {e}")
        # On error, assume change to be safe
        sys.exit(1)

if __name__ == "__main__":
    main()
