from gradio_client import Client

def check_api(space_name):
    print(f"--- Checking parameters for {space_name} ---")
    try:
        client = Client(space_name)
        client.view_api()
    except Exception as e:
        print(f"Error connecting to {space_name}: {e}")

if __name__ == "__main__":
    # check_api("yisol/IDM-VTON")
    check_api("levihsu/OOTDiffusion")
    check_api("Kwai-Kolors/Kolors-Virtual-Try-On") 
