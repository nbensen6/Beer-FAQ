import logging
import os

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
FAQ_CHANNEL_ID = int(os.environ["FAQ_CHANNEL_ID"]) if os.environ.get("FAQ_CHANNEL_ID") else None

GOOGLE_DOC_ID = "1BdpkJnoliRMklsYWkoK21ul4vWI9dW2MttsVbWMRaV0"
RULEBOOK_REFRESH_HOURS = 6

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("beer-faq")
