from gradio_client import Client

try:
    client = Client("levihsu/OOTDiffusion")
    print("Client info:")
    client.view_api()
except Exception as e:
    print(e)
