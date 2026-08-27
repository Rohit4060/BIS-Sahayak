import os
from google import genai
from google.genai import types

# Loads the GEMINI_API_KEY from the environment (set via .env in main.py)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are BIS Sahayak AI, an assistant that helps users understand
Indian Standards (IS) and Bureau of Indian Standards (BIS) processes, such as
product certification, compliance requirements, and standards lookup.

IMPORTANT — you must always follow this rule:
You are currently answering from your own general knowledge only. You are NOT
yet connected to any official, authoritative, or up-to-date BIS database or
document source. At the end of every answer, clearly and explicitly remind the
user of this, for example: "Note: This answer is based on general knowledge and
is not yet verified against official BIS documents. Please confirm with the
official BIS website or a BIS office before relying on this for compliance."

Keep answers clear, concise, and helpful for someone trying to understand BIS
and Indian Standards topics."""


def get_ai_response(user_message: str) -> str:
    """
    Sends the user's message to Gemini and returns the text reply.
    Raises an exception if the API call fails; the caller handles it.
    """
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=1000,
        ),
    )
    return response.text