"""
Virtual Key Management
Usage:
  python create_keys.py

Generate virtual keys for different business systems.
Each key can be scoped to specific models and budget.
"""
import requests

MASTER_KEY = "sk-my-master-key-1234"
PROXY_URL = "http://localhost:4000"


def generate_key(name, models, budget=None):
    payload = {
        "models": models,
        "metadata": {"system": name},
    }
    if budget:
        payload["max_budget"] = budget

    resp = requests.post(
        f"{PROXY_URL}/key/generate",
        headers={
            "Authorization": f"Bearer {MASTER_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    data = resp.json()
    print(f"[{name}]")
    print(f"  Key: {data.get('key', data.get('token', 'N/A'))}")
    print(f"  Models: {models}")
    if budget:
        print(f"  Budget: ${budget}/month")
    print()
    return data


# system-a: only MiniMax
generate_key("system-a", ["minimax-m2-5", "minimax-m2-7"], budget=10)

# system-b: only DeepSeek
generate_key("system-b", ["deepseek-v4-flash", "deepseek-v4-pro"], budget=20)

# system-c: all models
generate_key("system-c", ["minimax-m2-5", "minimax-m2-7", "deepseek-v4-flash", "deepseek-v4-pro", "glm-5-1"])

print("Done. Use the generated keys in your OpenAI client:")
print('  client = OpenAI(api_key="<generated_key>", base_url="http://localhost:4000/v1")')
