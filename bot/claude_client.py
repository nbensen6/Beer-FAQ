import asyncio
import functools
from pathlib import Path

import anthropic

from bot.config import ANTHROPIC_API_KEY, log

_RULEBOOK_PATH = Path(__file__).parent / "rulebook.txt"
_rulebook_text: str = ""
_client: anthropic.Anthropic | None = None

SYSTEM_PROMPT = """\
You are the Beer League FAQ Bot. You answer questions about the Beer League Rulebook (v3.2) \
for a League of Legends amateur competitive league.

Here is the complete rulebook:

<rulebook>
{rulebook}
</rulebook>

Instructions:
- Answer questions based ONLY on the rulebook above. If the answer is not in the rulebook, say so.
- Cite the relevant section number (e.g. "Section 4.4") when possible.
- Keep answers concise but complete. Use bullet points for multi-part answers.
- If a value is listed as "TBD" in the rulebook, say it hasn't been determined yet for this season.
- Be friendly and helpful. This is a community league — keep the tone casual.
- If someone asks something unrelated to the Beer League, politely redirect them.
"""


def _load_rulebook() -> str:
    global _rulebook_text
    if not _rulebook_text:
        _rulebook_text = _RULEBOOK_PATH.read_text(encoding="utf-8")
        log.info("Loaded rulebook: %d characters", len(_rulebook_text))
    return _rulebook_text


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _ask_sync(question: str) -> str:
    rulebook = _load_rulebook()
    client = _get_client()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT.format(rulebook=rulebook),
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text


async def ask_rulebook(question: str) -> str:
    """Ask a question about the rulebook. Runs the sync Anthropic SDK in a thread."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(_ask_sync, question))
