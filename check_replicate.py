import replicate
import os
from dotenv import load_dotenv

load_dotenv()

def check_model(model_name):
    print(f"Checking {model_name}...")
    try:
        model = replicate.models.get(model_name)
        print(f"Model found: {model.owner}/{model.name}")
        if model.latest_version:
            print(f"Latest version: {model.latest_version.id}")
            return f"{model_name}:{model.latest_version.id}"
        else:
            print("No latest version found.")
    except Exception as e:
        print(f"Error checking {model_name}: {e}")
    return None

# Check candidates
candidates = [
    "cuuupid/idm-vton",
    "ysolters/idm-vton",
    "kwai-kolors/kolors-virtual-try-on",
    "fashn/tryon"
]

valid_models = []
for c in candidates:
    ver = check_model(c)
    if ver:
        valid_models.append(ver)

print("\nValid Models Found:")
for m in valid_models:
    print(m)
