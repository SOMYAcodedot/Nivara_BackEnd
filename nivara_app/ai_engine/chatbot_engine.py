"""
Legacy chatbot response for POST /api/chat/ (single-message, no history).
For conversation with history, use POST /api/chat/nivara/ and generic_chat.
"""


def chatbot_response(user_message: str) -> str:
    """Single-turn response; delegates to generic_chat with empty history."""
    try:
        from .generic_chat import generate_chat_response
        from ..chat_formatting import compact_assistant_reply
        return compact_assistant_reply(generate_chat_response([], user_message))
    except Exception:
        return "Chat is temporarily unavailable. Please try again later."
