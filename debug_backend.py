from backend.clothes_manager import ClothesManager
import os

# Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "model", "衣服介紹.txt")

print(f"Testing data file: {DATA_FILE}")

try:
    manager = ClothesManager(DATA_FILE)
    clothes = manager.get_all_clothes()
    print(f"Successfully loaded {len(clothes)} items.")
    for c in clothes:
        print(c)
except Exception as e:
    print(f"CRASHED: {e}")
    import traceback
    traceback.print_exc()
