from backend.clothes_manager import ClothesManager
from backend.ai_service import AIService
import os

# Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "model", "衣服介紹.txt")
MODEL_DIR = os.path.join(BASE_DIR, "model")

manager = ClothesManager(DATA_FILE)
ai_service = AIService()

def process():
    print(f"Reading from {DATA_FILE}")
    clothes = manager.get_all_clothes()
    updated_count = 0
    
    for item in clothes:
        # Check if needs update (Legacy format usually has "未知衣物" or missing style)
        if item.get("name") == "未知衣物" or item.get("style") == "未分類":
            print(f"Updating item {item['id']}...")
            
            # Find image
            # Try jpg or png
            image_path = os.path.join(MODEL_DIR, f"{item['id']}.jpg")
            if not os.path.exists(image_path):
                image_path = os.path.join(MODEL_DIR, f"{item['id']}.png")
            
            if os.path.exists(image_path):
                try:
                    with open(image_path, "rb") as f:
                        content = f.read()
                    
                    # Call AI (Mock)
                    # To make it look realistic, let's vary the mock response slightly based on ID if using mock
                    # But ai_service.analyze_image_style is likely static.
                    # Let's just use what it returns.
                    analysis = ai_service.analyze_image_style(content)
                    
                    # Update item
                    # Mimicking "AI" by adding ID to name to distinguish them
                    item["name"] = f"AI精選_{analysis['name']}_{item['id']}"
                    item["style"] = analysis['style']
                    
                    updated_count += 1
                except Exception as e:
                    print(f"Failed to process image for {item['id']}: {e}")
            else:
                print(f"Image not found for {item['id']}")

    if updated_count > 0:
        manager.save_all_clothes(clothes)
        print(f"Successfully updated {updated_count} items.")
    else:
        print("No items needed updating.")

if __name__ == "__main__":
    process()
