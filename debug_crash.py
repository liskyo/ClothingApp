from fastapi.testclient import TestClient
from backend.main import app
import os
import sys

print("Initializing Test Client...")
client = TestClient(app)

print("Sending Request to /api/clothes...")
try:
    response = client.get("/api/clothes")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print("CRASHED DURING REQUEST!")
    print(e)
    import traceback
    traceback.print_exc()
