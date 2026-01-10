import os
import asyncio
from backend.clothes_manager import ClothesManager
from backend.ai_service import AIService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")
DATA_FILE = os.path.join(MODEL_DIR, "clothes.json")

import time

async def update_names():
    print("Initialize Managers...")
    manager = ClothesManager(DATA_FILE)
    ai_service = AIService()
    
    clothes = manager.get_all_clothes()
    print(f"Found {len(clothes)} items to process.")
    
    updated_count = 0
    
    for item in clothes:
        print(f"Processing {item['id']}...")
        
        # Try to find image
        image_path = os.path.join(MODEL_DIR, f"{item['id']}.jpg")
        if not os.path.exists(image_path):
            image_path = os.path.join(MODEL_DIR, f"{item['id']}.png")
            
        if os.path.exists(image_path):
            content = None
            with open(image_path, "rb") as f:
                content = f.read()
            
            # Retry loop
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"  - Analyzing image with Gemini (Attempt {attempt+1})...")
                    analysis = ai_service.analyze_image_style(content)
                    
                    new_name = analysis.get("name")
                    new_style = analysis.get("style")
                    
                    # Filter out mock responses if possible, but ai_service returns mock on error internally.
                    # We should check if it's the specific mock string.
                    if new_name and "Mock" not in new_name:
                        print(f"  - Update: {item['name']} -> {new_name} ({new_style})")
                        item['name'] = new_name
                        item['style'] = new_style
                        updated_count += 1
                        break # Success
                    else:
                        print(f"  - Got mock response: {new_name}")
                        # If it's a mock response due to error inside ai_service, it prints the error there.
                        # We can't easily detect 429 here unless we modify ai_service to raise.
                        # But let's assume if we get mock, we might want to wait and retry if it was rate limit?
                        # Actually ai_service swallows exception.
                        # For batch script, maybe we should just accept it or wait a bit.
                        time.sleep(2) 
                        
                except Exception as e:
                    print(f"  - Error in script: {e}")
                    time.sleep(5)
        else:
            print(f"  - Image not found for {item['id']}")

    if updated_count > 0:
        print(f"Saving {updated_count} updates to {DATA_FILE}...")
        manager.save_all_clothes(clothes)
        print("Done!")
    else:
        print("No updates made.")

if __name__ == "__main__":
    asyncio.run(update_names())
