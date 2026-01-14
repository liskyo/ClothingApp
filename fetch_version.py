import os
import replicate
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("REPLICATE_API_TOKEN")
print(f"Token present: {bool(token)}")

if not token:
    print("Error: No token found")
    exit(1)

try:
    client = replicate.Client(api_token=token)
    print("Fetching model cuuupid/idm-vton...")
    model = client.models.get("cuuupid/idm-vton")
    
    if model.latest_version:
        print(f"Latest Version ID: {model.latest_version.id}")
    else:
        print("Model found but no latest version (Result is None). Listing versions...")
        versions = model.versions.list()
        if versions:
            print(f"Most recent version: {versions[0].id}")
        else:
            print("No versions found.")
            
except Exception as e:
    print(f"Error: {e}")
