import os
import io
from PIL import Image
from backend.ai_service import AIService
from dotenv import load_dotenv

load_dotenv()

def create_dummy_pants_image():
    # Create a WIDE blue rectangle image representing folded jeans (to trigger aspect ratio fix)
    img = Image.new('RGB', (800, 600), (255, 255, 255))
    # Draw blue pants shape
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 700, 500], fill=(50, 100, 200)) 
    path = "dummy_pants_wide.jpg"
    img.save(path)
    return path

def main():
    print("Initializing AIService...")
    service = AIService()
    
    # Path to user image (from artifacts)
    user_img_path = r"C:\Users\liskyo\.gemini\antigravity\brain\bf0bec16-d2b5-41cc-bd94-8076de1e9832\uploaded_image_1768135372242.png"
    
    if not os.path.exists(user_img_path):
        print(f"User image not found at {user_img_path}")
        return

    print(f"Reading user image from {user_img_path}...")
    with open(user_img_path, "rb") as f:
        person_bytes = f.read()
        
    cloth_path = create_dummy_pants_image()
    print(f"Created dummy pants at {cloth_path}")
    
    print("Running virtual_try_on (Lower-body)...")
    try:
        # Call with explicit Lower-body category to trigger the optimized logic
        result = service.virtual_try_on(
            person_img_bytes=person_bytes,
            cloth_img_path=cloth_path,
            category="Lower-body",
            cloth_name="Test Jeans"
        )
        
        if result:
            out_path = "test_vton_result.jpg"
            with open(out_path, "wb") as f:
                f.write(result)
            print(f"SUCCESS: Result saved to {out_path}")
            print(f"Result size: {len(result)} bytes")
        else:
            print("FAILURE: Validation returned None or empty.")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
