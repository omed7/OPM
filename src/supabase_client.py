import os
import json
import urllib.request
import urllib.error

def get_supabase_config():
    # Support both SUPABASE and SUPERBASE spellings
    url = os.environ.get("SUPABASE_URL") or os.environ.get("SUPERBASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPERBASE_KEY")
    return url, key

def supabase_request(endpoint, method="GET", data=None):
    url, key = get_supabase_config()
    if not url or not key:
        return None, "Supabase URL or Key not configured"

    # Ensure URL ends without slash and endpoint starts with slash
    url = url.rstrip('/')
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint

    full_url = url + "/rest/v1" + endpoint

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(full_url, data=req_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = response.read()
            if response.getheader("Content-Type", "").startswith("application/json"):
                return json.loads(res_data.decode("utf-8")), None
            if res_data:
                try:
                    return json.loads(res_data.decode("utf-8")), None
                except Exception:
                    pass
            return [], None
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        return None, f"HTTP {e.code}: {error_body}"
    except Exception as e:
        return None, str(e)
