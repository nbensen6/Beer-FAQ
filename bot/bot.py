import discord
from discord import app_commands

from bot.config import DISCORD_TOKEN, FAQ_CHANNEL_ID, log
from bot.claude_client import ask_rulebook

MAX_RESPONSE_LENGTH = 1900


class BeerFAQBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        self.tree.add_command(_ask_command)
        await self.tree.sync()
        log.info("Slash commands synced")

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, self.user.id)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not self.user:
            return
        if self.user not in message.mentions:
            return
        if message.channel.id != FAQ_CHANNEL_ID:
            await message.reply(
                f"I only answer questions in <#{FAQ_CHANNEL_ID}>!",
                mention_author=False,
            )
            return

        question = message.content.replace(f"<@{self.user.id}>", "").strip()
        if not question:
            await message.reply(
                "Ask me a question about the Beer League rulebook!",
                mention_author=False,
            )
            return

        async with message.channel.typing():
            try:
                answer = await ask_rulebook(question)
            except Exception:
                log.exception("Claude API error")
                await message.reply(
                    "Sorry, I ran into an error. Try again in a moment.",
                    mention_author=False,
                )
                return

        for chunk in _split_message(answer):
            await message.reply(chunk, mention_author=False)


@app_commands.command(name="ask", description="Ask a question about the Beer League Rulebook")
@app_commands.describe(question="Your question about the Beer League rules")
async def _ask_command(interaction: discord.Interaction, question: str) -> None:
    if interaction.channel_id != FAQ_CHANNEL_ID:
        await interaction.response.send_message(
            f"I only answer questions in <#{FAQ_CHANNEL_ID}>!",
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True)

    try:
        answer = await ask_rulebook(question)
    except Exception:
        log.exception("Claude API error")
        await interaction.followup.send(
            "Sorry, I ran into an error. Try again in a moment."
        )
        return

    for i, chunk in enumerate(_split_message(answer)):
        if i == 0:
            await interaction.followup.send(chunk)
        else:
            await interaction.channel.send(chunk)


def _split_message(text: str) -> list[str]:
    """Split a long response into Discord-friendly chunks."""
    if len(text) <= MAX_RESPONSE_LENGTH:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= MAX_RESPONSE_LENGTH:
            chunks.append(text)
            break
        # Try to split at a newline
        split_at = text.rfind("\n", 0, MAX_RESPONSE_LENGTH)
        if split_at == -1:
            split_at = MAX_RESPONSE_LENGTH
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


def main() -> None:
    bot = BeerFAQBot()
    bot.run(DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
