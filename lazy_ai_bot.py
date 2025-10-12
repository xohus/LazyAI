import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

API_URL = "https://router.huggingface.co/v1/chat/completions"
HF_TOKEN = os.environ.get("HF_TOKEN")

headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

def query(prompt):
    payload = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "model": "meta-llama/Llama-3-8b-chat-hf",  # ✅ or another router-supported model
        "max_tokens": 512,
        "temperature": 0.7
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]
    else:
        print("Error:", response.status_code, response.text)
        return "⚠️ Lazy.AI is sleepy. Try again later."

# Example usage
if __name__ == "__main__":
    user_input = input("🧠 Ask Lazy.AI: ")
    reply = query(user_input)
    print(f"Lazy.AI: {reply}")
