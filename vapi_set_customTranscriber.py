import requests

# ⬇️ Replace with your actual keys and assistant ID
VAPI_API_KEY = "78d9675a-a10c-4d62-97ae-2e13e88f620d"  # Your VAPI private key
ASSISTANT_ID = "3292e2b9-610b-4118-9cce-e71162af40a7"
WS_URL = "wss://sarvamstt.onrender.com/ws"

url = f"https://api.vapi.ai/assistant/{ASSISTANT_ID}"
headers = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json"
}
payload = {
    "transcriber": {
        "provider": "custom-transcriber",
        "server": {
            "url": WS_URL
        }
    }
}

response = requests.patch(url, json=payload, headers=headers)
print("Status:", response.status_code)
print("Response:", response.json())
