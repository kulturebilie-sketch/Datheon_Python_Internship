import json
import re
import sys
import traceback
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# The FAQ JSON file is expected to live next to this script.
FAQ_PATH = Path(__file__).parent / "sample_faq.json"

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def load_faq(path: Path) -> dict:
    """Load and validate the FAQ data.

    The file must contain a JSON object with two keys:
    * ``greetings`` – a list of greeting strings.
    * ``faqs`` – a list of ``{"question": ..., "answer": ...}`` objects.
    Returns a dictionary with normalised greetings and a list of validated FAQs.
    """
    if not path.is_file():
        print(f"[Error] FAQ file not found: {path}")
        return {"greetings": [], "faqs": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Root element must be a JSON object.")
        greetings = data.get("greetings", [])
        faqs = data.get("faqs", [])
        if not isinstance(greetings, list) or not isinstance(faqs, list):
            raise ValueError("'greetings' and 'faqs' must be lists.")
        # Normalise greetings (lower‑case, stripped)
        clean_greetings = [g.strip().lower() for g in greetings if isinstance(g, str) and g.strip()]
        # Validate each FAQ entry
        clean_faqs = []
        for item in faqs:
            if (
                isinstance(item, dict)
                and isinstance(item.get("question"), str)
                and isinstance(item.get("answer"), str)
            ):
                clean_faqs.append({
                    "question": item["question"].strip(),
                    "answer": item["answer"].strip(),
                })
        return {"greetings": clean_greetings, "faqs": clean_faqs}
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[Error] Failed to load FAQ file: {exc}")
        return {"greetings": [], "faqs": []}

# Load once at import time
FAQ_DATA = load_faq(FAQ_PATH)

# ---------------------------------------------------------------------------
# Text processing utilities
# ---------------------------------------------------------------------------
STOP_WORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "how",
    "i", "in", "is", "me", "my", "of", "the", "to", "what",
    "when", "will", "you", "your", "we", "our",
}

SYNONYMS = {
    "get": "receive",
    "getting": "receive",
    "obtain": "receive",
    "obtaining": "receive",
    "issued": "receive",
    "issuance": "receive",
    "certificates": "certificate",
    "certification": "certificate",
    "submitting": "submit",
    "upload": "submit",
    "uploaded": "submit",
    "send": "submit",
    "opening": "hours",
    "operating": "hours",
    "operation": "hours",
    "closed": "hours",
    "open": "hours",
}

def normalize(text: str) -> str:
    """Lower‑case, strip, and collapse whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())

def get_words(text: str) -> set:
    """Return a set of meaningful tokens from *text*.

    Synonyms are applied and stop‑words are removed.
    """
    tokens = re.findall(r"[a-z0-9]+", normalize(text))
    return {SYNONYMS.get(tok, tok) for tok in tokens if tok not in STOP_WORDS}

# ---------------------------------------------------------------------------
# Intent matching – multi‑intent aware
# ---------------------------------------------------------------------------
def score_match(query_words: set, faq_question: str) -> float:
    """Return a similarity score between the query and a FAQ question.

    The score is the ratio of overlapping meaningful words to the total words
    in the FAQ question. A score of 0 means no overlap; 1 means a perfect match.
    """
    q_words = get_words(faq_question)
    if not q_words:
        return 0.0
    common = query_words.intersection(q_words)
    return len(common) / len(q_words)

def find_best_faqs(user_input: str, top_n: int = 2, min_score: float = 0.3) -> List[Tuple[dict, float]]:
    """Return up to *top_n* FAQs that exceed *min_score*.

    Each entry is a tuple ``(faq_dict, score)`` ordered by descending score.
    """
    query_words = get_words(user_input)
    if not query_words:
        return []
    scored = []
    for faq in FAQ_DATA["faqs"]:
        s = score_match(query_words, faq["question"])
        if s >= min_score:
            scored.append((faq, s))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]

def is_greeting(user_input: str) -> bool:
    """Check whether the input matches a known greeting."""
    msg = normalize(user_input)
    for g in FAQ_DATA["greetings"]:
        if msg == g or msg.startswith(g + " "):
            return True
    return False

# ---------------------------------------------------------------------------
# Main REPL loop with robust error handling
# ---------------------------------------------------------------------------
EXIT_COMMANDS = {"bye", "exit", "quit"}

def get_response(matches: List[Tuple[dict, float]]) -> str:
    """Create a user‑facing response from *matches*.

    - No matches → a polite fallback.
    - Single match → the answer directly.
    - Multiple matches → enumerate the relevant answers.
    """
    if not matches:
        return (
            "I'm sorry, I didn't understand that. Could you rephrase? "
            "You can ask about operating hours, internship project submission, "
            "or certificate delivery."
        )
    if len(matches) == 1:
        return matches[0][0]["answer"]
    # Multiple intents – combine answers
    parts = [f"• {m[0]["answer"]}" for m in matches]
    return "I found several relevant answers:\n" + "\n".join(parts)

def main():
    print("Customer Support Bot – type 'bye', 'exit', or 'quit' to end the conversation.")
    if not FAQ_DATA["faqs"]:
        print("[Warning] No FAQs loaded – check sample_faq.json.")
    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nBot: Goodbye! Have a great day.")
            break
        try:
            norm = normalize(user_input)
            if norm in EXIT_COMMANDS:
                print("Bot: Goodbye! Have a great day.")
                break
            if not norm:
                print("Bot: Please type a question.")
                continue
            if is_greeting(norm):
                print("Bot: Hello! How can I assist you today?")
                continue
            matches = find_best_faqs(user_input)
            print(f"Bot: {get_response(matches)}")
        except Exception as exc:
            # Catch‑all to avoid the bot crashing on unexpected errors.
            print("Bot: Oops, something went wrong. Please try again.")
            print("[Debug]", "".join(traceback.format_exception(None, exc, exc.__traceback__)))
            # Optionally, exit on severe errors – here we just continue.

if __name__ == "__main__":
    main()
