from gradio_client import Client

spaces = [
    "human37/IDM-VTON",
    "KWai-Kolors/Kolors-Virtual-Try-On",
    "levihsu/OOTDiffusion"
]

for space in spaces:
    print(f"--- Checking {space} ---")
    try:
        client = Client(space)
        client.view_api()
        print(f"--- SUCCESS: {space} ---")
    except Exception as e:
        print(f"Error checking {space}: {e}")
