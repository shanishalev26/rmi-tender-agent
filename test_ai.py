import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()              # קורא את .env ומכניס את המפתח לסביבה
client = Anthropic()       # קורא אוטומטית את ANTHROPIC_API_KEY

msg = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=200,
    messages=[{"role": "user", "content": "ענה במשפט אחד בעברית: מה זה מכרז מקרקעין?"}],
)
print(msg.content[0].text)