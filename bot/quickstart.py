import os
import anthropic
from dotenv import load_dotenv

load_dotenv()
claude_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1000,
    messages=[
        {
            "role": "user",
            "content": "What should I search for to find the latest Minecraft update notes?",
        }
    ],
)
print(message.content)
