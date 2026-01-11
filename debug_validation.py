import os
import sys
from dotenv import load_dotenv

# Load env vars first
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Add project root to path
sys.path.append(os.path.dirname(__file__))

from backend.ai_service import AIService

def test_validation():
    service = AIService()
    
    # Path to the user's uploaded image (from metadata)
    img_path = r"C:/Users/liskyo/.gemini/antigravity/brain/bf0bec16-d2b5-41cc-bd94-8076de1e9832/uploaded_image_1768130701560.png"
    
    if not os.path.exists(img_path):
        print(f"Error: Image not found at {img_path}")
        return

    print(f"Testing validation on: {img_path}")
    
    with open(img_path, "rb") as f:
        img_bytes = f.read()
        
    result = service.validate_and_crop_user_photo(img_bytes)
    
    print("-" * 30)
    print("VALIDATION RESULT:")
    print(f"Valid: {result.get('valid')}")
    print(f"Reason: {result.get('reason')}")
    # Don't print the huge binary processed_image
    if result.get('processed_image'):
        print("Processed Image: [Bytes Present]")
    else:
        print("Processed Image: None")
    print("-" * 30)

if __name__ == "__main__":
    test_validation()
