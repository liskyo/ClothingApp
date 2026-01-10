from gradio_client import Client
import sys

spaces = [
    "KWai-Kolors/Kolors-Virtual-Try-On",
    "levihsu/OOTDiffusion"
]

with open("gradio_api_info.txt", "w", encoding="utf-8") as f:
    for space in spaces:
        f.write(f"\n--- Checking {space} ---\n")
        try:
            client = Client(space)
            # Redirect stdout to file to capture view_api
            original_stdout = sys.stdout
            sys.stdout = f
            client.view_api()
            sys.stdout = original_stdout
            f.write(f"\n--- SUCCESS: {space} ---\n")
        except Exception as e:
            sys.stdout = sys.__stdout__ # Restore just in case
            f.write(f"Error checking {space}: {e}\n")
