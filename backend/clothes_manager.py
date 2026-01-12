import json
import os
from typing import List, Dict, Optional
import time

class ClothesManager:
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.use_mongo = False
        self.db = None
        self.collection = None
        
        # Check for MongoDB URI
        mongo_uri = os.getenv("MONGODB_URI")
        if mongo_uri:
            try:
                from pymongo import MongoClient
                self.client = MongoClient(mongo_uri)
                self.db = self.client.get_database("clothing_app")
                self.collection = self.db.get_collection("clothes")
                self.use_mongo = True
                print("ClothesManager: Connected to MongoDB Atlas.")
            except Exception as e:
                print(f"ClothesManager: Failed to connect to MongoDB ({e}). Falling back to local JSON.")
        
        if not self.use_mongo:
            # Fallback for Vercel: Look in the same directory as this file
            if not os.path.exists(self.data_file):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                possible_path = os.path.join(base_dir, "../model/clothes.json")
                if os.path.exists(possible_path):
                    self.data_file = possible_path
            self.ensure_file_exists()

    def ensure_file_exists(self):
        if self.use_mongo: return
        
        if os.path.exists(self.data_file):
            return

        print(f"Warning: Data file not found at {self.data_file}")
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)
        except OSError as e:
            # Important for Vercel: If read-only, we just log and continue.
            # The app will work but data won't persist if not using Mongo.
            print(f"Could not create data file (Read-Only Filesystem?): {e}")
            print("Running in volatile mode (In-Memory only if no DB).")

    def get_status(self) -> Dict:
        count = -1
        try:
            if self.use_mongo and self.collection is not None:
                count = self.collection.count_documents({})
            else:
                 # Fallback to local list length if not using mongo or collection is None
                 # But get_all_clothes itself might attempt mongo read
                 # So we need to be careful.
                 # Let's just try get_all_clothes which has fallback?
                 # Actually get_all_clothes() has logic inside.
                 # Let's just catch specific error.
                 count = len(self.get_all_clothes())
        except Exception as e:
            print(f"Error getting item count: {e}")
            count = -1
            
        return {
            "mode": "MongoDB" if self.use_mongo else "Local JSON (Volatile on Vercel)",
            "mongo_connected": self.use_mongo,
            "item_count": count
        }

    def get_all_clothes(self) -> List[Dict]:
        if self.use_mongo:
            try:
                # Exclude _id from result or convert it to string
                cursor = self.collection.find({}, {'_id': 0})
                return list(cursor)
            except Exception as e:
                print(f"MongoDB Read Error: {e}")
                return []
        
        # Local JSON Fallback
        if not os.path.exists(self.data_file):
            return []

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON. Returning empty list.")
            return []

    def get_cloth_by_id(self, cloth_id: str) -> Optional[Dict]:
        if self.use_mongo:
            try:
                # Try finding by exact ID or ID without extension
                raw_id = cloth_id.replace('.jpg', '').replace('.png', '')
                # Note: We store "id" in doc.
                item = self.collection.find_one({"id": raw_id}, {'_id': 0})
                if not item:
                     # Try fallback search if ID format mismatch
                     item = self.collection.find_one({"id": cloth_id}, {'_id': 0})
                return item
            except Exception as e:
                print(f"MongoDB Find Error: {e}")
                return None

        clothes = self.get_all_clothes()
        for item in clothes:
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
                curr_id_str = str(item.get('id', '')).replace('.jpg', '').replace('.png', '')
                if curr_id_str.isdigit():
                    curr_id = int(curr_id_str)
                    if curr_id > max_id:
                        max_id = curr_id
            
            return f"{max_id + 1:03d}"
        except Exception as e:
            print(f"Error calculating next ID: {e}")
            return f"999{int(time.time())}" # Safe fallback

    def add_clothing_item(self, name: str, height_range: str, gender: str, style: str, category: str = "Upper-body", image_url: str = "") -> str:
        """
        Adds a new clothing item. Returns its ID.
        """
        new_id = self.get_next_id()
        
        new_item = {
            "id": new_id,
            "name": name,
            "height_range": height_range,
            "gender": gender,
            "style": style,
            "category": category,
            "image_url": image_url # Store the full URL (Cloudinary or Local)
        }
        
        if self.use_mongo:
            try:
                self.collection.insert_one(new_item)
                print(f"ClothesManager: Added item {new_id} to MongoDB.")
            except Exception as e:
                print(f"MongoDB Insert Error: {e}")
                # Fallback to local if DB fails? No, simpler to just fail or retry.
        else:
            clothes = self.get_all_clothes()
            clothes.append(new_item)
            self.save_all_clothes(clothes)
            
        return new_id

    def delete_clothing_item(self, cloth_id: str) -> bool:
        """
        Deletes a clothing item by ID.
        """
        if self.use_mongo:
            try:
                # Handle ID with or without extension
                raw_id = cloth_id.replace('.jpg', '').replace('.png', '')
                result = self.collection.delete_one({"id": raw_id})
                if result.deleted_count == 0:
                     # Try fallback
                     result = self.collection.delete_one({"id": cloth_id})
                return result.deleted_count > 0
            except Exception as e:
                print(f"MongoDB Delete Error: {e}")
                return False
        
        # Local JSON
        clothes = self.get_all_clothes()
        original_len = len(clothes)
        # Filter out the item
        clothes = [c for c in clothes if c['id'] != cloth_id and c['id'] != cloth_id.replace('.jpg', '')]
        
        if len(clothes) < original_len:
            self.save_all_clothes(clothes)
            return True
        return False

    def update_clothing_item(self, cloth_id: str, updates: Dict) -> bool:
        """
        Updates a clothing item fields.
        """
        if self.use_mongo:
            try:
                raw_id = cloth_id.replace('.jpg', '').replace('.png', '')
                # Try update
                result = self.collection.update_one({"id": raw_id}, {"$set": updates})
                if result.matched_count == 0:
                     result = self.collection.update_one({"id": cloth_id}, {"$set": updates})
                return result.matched_count > 0
            except Exception as e:
                print(f"MongoDB Update Error: {e}")
                return False

        # Local JSON
        clothes = self.get_all_clothes()
        found = False
        for c in clothes:
            if c['id'] == cloth_id or c['id'] == cloth_id.replace('.jpg', ''):
                c.update(updates)
                found = True
                break
        
        if found:
            self.save_all_clothes(clothes)
        return found

    def save_all_clothes(self, clothes_list: List[Dict]):
        if self.use_mongo:
            print("Warning: Bulk save not implemented for MongoDB mode.")
            return

        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(clothes_list, f, ensure_ascii=False, indent=4)
        except OSError as e:
            print(f"Failed to save data file (Read-Only FS?): {e}")
