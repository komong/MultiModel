"""
LiteLLM Proxy
 1.  proxy: python start_proxy.py
 2.  python test_call.py
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key="sk-my-master-key-1234",
    base_url="http://localhost:4800/v1",
)

models = [
    ("minimax-m2-5", "1+1=?"),
    ("minimax-m2-7", "1+1=?"),
    ("deepseek-v4-flash", "1+1=?"),
    ("deepseek-v4-pro", "1+1=?"),
    ("glm-5-1", "1+1=?"),
]

for model_name, prompt in models:
    print(f"\n{'='*50}")
    print(f"Model: {model_name}")
    print(f"{'='*50}")
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"ERROR: {e}")

print("\n\nAll tests done")
