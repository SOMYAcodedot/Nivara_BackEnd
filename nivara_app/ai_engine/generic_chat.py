"""
Nivara Women's Health AI System
================================
Module : Generic Wellness Chatbot
LLM    : Azure OpenAI — GPT-4o mini

This module provides a backend-ready conversational chatbot
for women's wellness questions.

Key Features
------------
✔ Azure OpenAI integration
✔ Conversation history support (client or DB-backed session)
✔ Input validation
✔ History token control (sliding window, one API call per message)
✔ Retry mechanism
✔ Logging for debugging
✔ Safety guard for medical responses
✔ Compact readable lists (single line per bullet, no extra blank lines)

Cost: one GPT completion per call to generate_chat_response (no chaining).

Environment variables (.env):
    AZURE_OPENAI_API_KEY
    AZURE_OPENAI_ENDPOINT
    AZURE_OPENAI_CHAT_DEPLOYMENT
    AZURE_OPENAI_API_VERSION
"""

# --------------------------------------------------
# Imports
# --------------------------------------------------

import os
import time
import logging
from openai import AzureOpenAI
from dotenv import load_dotenv

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()

# --------------------------------------------------
# Configure logging (important for production)
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nivara-chat")

# --------------------------------------------------
# Azure OpenAI client setup
# --------------------------------------------------

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
if not DEPLOYMENT_NAME:
    raise ValueError("AZURE_OPENAI_CHAT_DEPLOYMENT is missing in .env")

# --------------------------------------------------
# System Prompt
# --------------------------------------------------

SYSTEM_PROMPT = """
You are Nivara, a warm and knowledgeable women's health and wellness AI assistant.

You help women with questions about health, nutrition, menstrual health,
emotional wellbeing, sleep, and lifestyle.

If the user asks medical diagnosis or treatment,
respond supportively but encourage consulting a doctor.

Guidelines:
- Be warm and empathetic — like a knowledgeable friend
- Validate feelings before giving suggestions
- Never diagnose medical conditions
- Encourage consulting a doctor for medical issues
- Use conversation history when relevant

Formatting (professional, tight — no vertical gaps):
- Never use two line breaks in a row. One newline only between lines.
"""

# --------------------------------------------------
# Configuration constants
# --------------------------------------------------

MAX_INPUT_CHARS = 1500
MAX_HISTORY_TURNS = 8 #means 8 turns of conversation (user-Q + ai-ans) total 16 messages -sliding window memory.always latest 8 turns 
MAX_RETRIES = 3

# --------------------------------------------------
# Medical trigger words (moved outside function)
# --------------------------------------------------

MEDICAL_TRIGGER_WORDS = [
    "diagnosis",
    "disease",
    "infection",
    "disorder",
    "treatment",
    "medication",
    "prescription",
    "dosage",
    "pcos",
    "endometriosis"
]

# --------------------------------------------------
# Core LLM response generator
# COST: Exactly ONE Azure OpenAI API call per invocation.
# History + current message are sent in a single request (no extra calls).
# --------------------------------------------------

def generate_chat_response(history_list: list[dict], current_query: str) -> str:

    """
    Generate a chatbot response using Azure OpenAI.
    Single call: history + current_query sent together; one API charge per user message.

    Parameters
    ----------
    history_list : list
        Previous conversation turns
    current_query : str
        User's latest message

    Returns
    -------
    str
        Assistant response or error message
    """

    # --------------------------------------------------
    # Clean input early
    # --------------------------------------------------

    current_query = current_query.strip()

    if not current_query:
        return "I didn't catch that — could you rephrase your question?"

    if len(current_query) > MAX_INPUT_CHARS:
        return "Your message is quite long. Could you shorten it a bit?"

    logger.info("User message received: %s", current_query)

    # --------------------------------------------------
    # Limit conversation history
    # --------------------------------------------------

    history_list = history_list[-MAX_HISTORY_TURNS:]

    # --------------------------------------------------
    # Build messages
    # --------------------------------------------------

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for turn in history_list:

        if turn.get("human_msg"):
            messages.append({
                "role": "user",
                "content": turn["human_msg"]
            })

        if turn.get("ai_msg"):
            messages.append({
                "role": "assistant",
                "content": turn["ai_msg"]
            })

    messages.append({
        "role": "user",
        "content": current_query
    })

    # --------------------------------------------------
    # Retry mechanism
    # --------------------------------------------------

    for attempt in range(MAX_RETRIES):

        try:

            response = client.chat.completions.create(
                model=DEPLOYMENT_NAME,
                messages=messages,
                temperature=0.7,
                max_tokens=400,
                timeout=20
            )

            reply = response.choices[0].message.content.strip()

            # Fallback if model returns empty output
            if not reply:
                reply = (
                    "I'm here to help. Could you tell me a bit more "
                    "about what you're experiencing?"
                )

            logger.info("LLM reply generated")

            # --------------------------------------------------
            # Safety guard
            # --------------------------------------------------

            if any(word in reply.lower() for word in MEDICAL_TRIGGER_WORDS):
                reply += (
                    "\n\nFor medical concerns it's always best to consult "
                    "a qualified healthcare professional."
                )

            return reply

        except Exception as e:

            error_str = str(e)
            logger.error("LLM error attempt %s: %s", attempt + 1, error_str)

            if attempt == MAX_RETRIES - 1:

                if "404" in error_str:
                    return (
                        f"[Error 404] Deployment '{DEPLOYMENT_NAME}' not found.\n"
                        "Check your Azure OpenAI deployment name."
                    )

                if "401" in error_str:
                    return "[Error 401] Invalid API key."

                if "429" in error_str:
                    return "[Error 429] Rate limit exceeded. Try again later."

                return f"[Error] {error_str}"

            time.sleep(2 ** attempt)

# --------------------------------------------------
# Stateful chat session class
# --------------------------------------------------

class NivaraChat:
    """
    Manages conversation state for a user session.

    Example usage:
        chat = NivaraChat()
        chat.send("What helps with cramps?")
        chat.send("What about teas?")
    """

    def __init__(self):
        self.history: list[dict] = []

    def send(self, user_message: str) -> str:

        reply = generate_chat_response(self.history, user_message)

        if not reply.startswith("[Error"):

            self.history.append({
                "human_msg": user_message,
                "ai_msg": reply
            })

            self.history = self.history[-MAX_HISTORY_TURNS:]

        return reply

    def reset(self):
        self.history = []

# --------------------------------------------------
# Local testing
# --------------------------------------------------

if __name__ == "__main__":

    chat = NivaraChat()

    print("Nivara:", chat.send("What foods help reduce bloating during my period?"))
    print("Nivara:", chat.send("Are there any teas that help?"))































