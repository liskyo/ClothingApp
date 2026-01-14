import os
import replicate
from dotenv import load_dotenv

load_dotenv("backend/.env")

api_token = os.getenv("REPLICATE_API_TOKEN")
if not api_token:
    print("Error: REPLICATE_API_TOKEN not found.")
    exit(1)

client = replicate.Client(api_token=api_token)

model_id = "cuuupid/idm-vton"
# Using the specific version we hardcoded to be sure
version_id = "0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985"

try:
    model = client.models.get(model_id)
    version = model.versions.get(version_id)
    
    print(f"--- Schema for {model_id}:{version_id} ---")
    print("Input Schema:")
    for key, prop in version.openapi_schema['components']['schemas']['Input']['properties'].items():
        print(f" - {key}: {prop.get('description', 'No description')}")
        if 'enum' in prop:
            print(f"   Enum: {prop['enum']}")
            
except Exception as e:
    print(f"Error fetching schema: {e}")
