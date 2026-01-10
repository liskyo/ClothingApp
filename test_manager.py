from backend.clothes_manager import ClothesManager
import os

def test_clothes_manager():
    test_file = "test_db.txt"
    if os.path.exists(test_file):
        os.remove(test_file)
        
    manager = ClothesManager(test_file)
    
    # Test initial state
    assert len(manager.get_all_clothes()) == 0, "Should be empty initially"
    
    # Test adding item
    id1 = manager.add_clothing_item("Test_Shirt", "160-170cm", "中性", "Casual")
    assert id1 == "001", f"First ID should be 001, got {id1}"
    
    # Test reading back
    items = manager.get_all_clothes()
    assert len(items) == 1
    assert items[0]['name'] == "Test_Shirt"
    assert items[0]['style'] == "Casual"
    
    # Test second item
    id2 = manager.add_clothing_item("Test Skirt", "150-160cm", "女性", "Formal")
    assert id2 == "002", f"Second ID should be 002, got {id2}"
    
    print("All ClothesManager tests passed!")
    
    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_clothes_manager()
