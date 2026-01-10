import json
import os
from typing import List, Dict, Optional

class ClothesManager:
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.ensure_file_exists()

    def ensure_file_exists(self):
        if not os.path.exists(self.data_file):
            print(f"Creating new data file at {self.data_file}")
            # Initialize with empty list
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)

    def get_all_clothes(self) -> List[Dict]:
        if not os.path.exists(self.data_file):
            return []

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON. Returning empty list.")
            return []

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

    def add_clothing_item(self, name: str, height_range: str, gender: str, style: str) -> str:
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
            "style": style
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
