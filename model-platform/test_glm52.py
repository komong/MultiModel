"""
Test GLM-5.2 through the local LiteLLM proxy.

Start the proxy first:
  py start_proxy.py
"""
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key="sk-my-master-key-1234",
    base_url="http://localhost:4800/v1",
)

response = client.chat.completions.create(
    model="glm-5-2",
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "Reply in one short sentence: is GLM-5.2 connected successfully?"},
    ],
    max_tokens=1024,
    temperature=0.6,
    extra_body={"thinking": {"type": "disabled"}},
)

message = response.choices[0].message
content = message.content or ""
if not content.strip():
    print(response.model_dump_json(indent=2))
else:
    print(content)
