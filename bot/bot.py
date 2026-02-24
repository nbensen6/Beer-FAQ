import asyncio

import discord
from discord import app_commands

from bot.config import DISCORD_TOKEN, FAQ_CHANNEL_ID, RULEBOOK_REFRESH_HOURS, log
from bot.claude_client import ask_rulebook, refresh_rulebook

MAX_RESPONSE_LENGTH = 1900


class BeerFAQBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.faq_channel_id: int | None = FAQ_CHANNEL_ID

    async def setup_hook(self) -> None:
        self.tree.add_command(self._make_ask_command())
        self.tree.add_command(self._make_setchannel_command())
        await self.tree.sync()
        log.info("Slash commands synced")

    def _make_ask_command(self) -> app_commands.Command:
        bot = self

        @app_commands.command(
            name="ask",
            description="Ask a question about the Beer League Rulebook",
        )
        @app_commands.describe(question="Your question about the Beer League rules")
        async def ask(interaction: discord.Interaction, question: str) -> None:
            if bot.faq_channel_id and interaction.channel_id != bot.faq_channel_id:
                await interaction.response.send_message(
                    f"I only answer questions in <#{bot.faq_channel_id}>!",
                    ephemeral=True,
                )
                return

            if not bot.faq_channel_id:
                await interaction.response.send_message(
                    "No FAQ channel set yet. An admin needs to run `/setchannel` first.",
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

        return ask

    def _make_setchannel_command(self) -> app_commands.Command:
        bot = self

        @app_commands.command(
            name="setchannel",
            description="Set this channel as the Beer FAQ channel (admin only)",
        )
        @app_commands.default_permissions(manage_guild=True)
        async def setchannel(interaction: discord.Interaction) -> None:
            bot.faq_channel_id = interaction.channel_id
            log.info(
                "FAQ channel set to #%s (%s) by %s",
                interaction.channel.name if interaction.channel else "unknown",
                interaction.channel_id,
                interaction.user,
            )
            await interaction.response.send_message(
                f"This channel is now the Beer FAQ channel! "
                f"Use `/ask` or @mention me here to ask questions about the rulebook.",
            )

        return setchannel

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, self.user.id)
        if self.faq_channel_id:
            log.info("FAQ channel: %s", self.faq_channel_id)
        else:
            log.info("No FAQ channel set — use /setchannel in Discord")
        self.loop.create_task(self._refresh_rulebook_loop())

    async def _refresh_rulebook_loop(self) -> None:
        """Periodically re-fetch the rulebook from Google Docs."""
        await self.wait_until_ready()
        interval = RULEBOOK_REFRESH_HOURS * 3600
        while not self.is_closed():
            await asyncio.sleep(interval)
            try:
                await refresh_rulebook()
            except Exception:
                log.exception("Rulebook refresh task error")

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not self.user:
            return
        if self.user not in message.mentions:
            return

        if not self.faq_channel_id:
            await message.reply(
                "No FAQ channel set yet. An admin needs to run `/setchannel` first.",
                mention_author=False,
            )
            return

        if message.channel.id != self.faq_channel_id:
            await message.reply(
                f"I only answer questions in <#{self.faq_channel_id}>!",
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


def _split_message(text: str) -> list[str]:
    """Split a long response into Discord-friendly chunks."""
    if len(text) <= MAX_RESPONSE_LENGTH:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= MAX_RESPONSE_LENGTH:
            chunks.append(text)
            break
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
