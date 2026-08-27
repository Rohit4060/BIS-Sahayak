"""
Quick test script for POST /api/search.

1. Make sure the backend is running first:
   uvicorn main:app --reload --port 8000

2. Then run:
   python scripts/test_search.py "What are the requirements for electrical appliances?"
"""
import sys
import json
import requests

query = sys.argv[1] if len(sys.argv) > 1 else "What are the requirements for electrical appliances?"

response = requests.post(
    "http://localhost:8000/api/search",
    json={"query": query, "top_k": 5},
)

print(f"Status code: {response.status_code}")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))