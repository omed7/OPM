import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.supabase_client import supabase_request
print(supabase_request('/matches?league=eq.mls&limit=2'))
