import os
import replicate
from dotenv import load_dotenv
import json

load_dotenv(".env")
token = os.getenv("REPLICATE_API_TOKEN")
if not token:
    print("❌ Token NOT found in env.")
    # Try reading manually
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("REPLICATE_API_TOKEN="):
                    os.environ["REPLICATE_API_TOKEN"] = line.split("=", 1)[1].strip()
                    print("✅ Token manually loaded from .env")
    except:
        pass
else:
    print("✅ Token found in env.")

try:
    print("Checking Replicate Model Schema...")
    model_name = "cuuupid/idm-vton"
    model = replicate.models.get(model_name)
    version = model.latest_version
    
    print(f"Model: {model_name}")
    print(f"Version ID: {version.id}")
    
    # Print Schema
    schema = version.openapi_schema.get("components", {}).get("schemas", {}).get("Input", {})
    print("\n--- Input Schema ---")
    properties = schema.get("properties", {})
    for key, val in properties.items():
        desc = val.get("description", "No description")
        default = val.get("default", "No default")
        print(f"- {key}: {desc} (Default: {default})")
        
except Exception as e:
    print(f"Error: {e}")
