import json
import os
from typing import List, Dict, Optional

class ClothesManager:
    def __init__(self, data_file: str):
        self.data_file = data_file
        # Try to resolve relative path if absolute path not found
        if not os.path.exists(self.data_file):
            # Fallback for Vercel: Look in the same directory as this file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            possible_path = os.path.join(base_dir, "../model/clothes.json")
            if os.path.exists(possible_path):
                print(f"File found at alternative path: {possible_path}")
                self.data_file = possible_path
            
        self.ensure_file_exists()

    def ensure_file_exists(self):
        # In Vercel (Read-Only), verifying existence is key. We cannot write.
        if os.path.exists(self.data_file):
            return

        print(f"Warning: Data file not found at {self.data_file}")
        # Only try to write if we are sure we can (e.g. not /var/task)
        # But for now, let's try to catch the error to prevent crash
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)
        except OSError as e:
            print(f"Could not create data file (likely read-only FS): {e}")

    def get_all_clothes(self) -> List[Dict]:
        if not os.path.exists(self.data_file):
            return []

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON. Returning empty list.")
            return []

    def get_cloth_by_id(self, cloth_id: str) -> Optional[Dict]:
        clothes = self.get_all_clothes()
        for item in clothes:
            # Handle both with and without extension in ID just in case
            if item['id'] == cloth_id or item['id'] == cloth_id.replace('.jpg', ''):
                return item
        return None

    def get_next_id(self) -> str:
        clothes = self.get_all_clothes()
        if not clothes:
            return "001"
        
        try:
            max_id = 0
            for item in clothes:
                # Filter out purely numeric IDs for calculation
                curr_id_str = item['id'].replace('.jpg', '').replace('.png', '')
                if curr_id_str.isdigit():
                    curr_id = int(curr_id_str)
                    if curr_id > max_id:
                        max_id = curr_id
            
            return f"{max_id + 1:03d}"
        except Exception as e:
            print(f"Error calculating next ID: {e}")
            return f"999" # Fallback

    def add_clothing_item(self, name: str, height_range: str, gender: str, style: str, category: str = "Upper-body") -> str:
        """
        Adds a new clothing item to the file and returns its ID.
        """
        clothes = self.get_all_clothes()
        new_id = self.get_next_id()
        
        new_item = {
            "id": new_id,
            "name": name,
            "height_range": height_range,
            "gender": gender,
            "style": style,
            "category": category
        }
        
        clothes.append(new_item)
        self.save_all_clothes(clothes)
            
        return new_id

    def save_all_clothes(self, clothes_list: List[Dict]):
        """
        Overwrites the file with the provided list of clothes.
        """
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(clothes_list, f, ensure_ascii=False, indent=4)
