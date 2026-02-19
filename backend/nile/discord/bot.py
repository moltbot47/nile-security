"""NILE Discord bot — real-time research layer for the ecosystem."""

import asyncio
import json
import logging
from datetime import UTC, datetime

import discord
import redis.asyncio as aioredis
from discord import app_commands

from nile.config import settings

logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True


class NileBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.redis: aioredis.Redis | None = None
        self._listener_task: asyncio.Task | None = None

    async def setup_hook(self) -> None:
        self.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        if settings.discord_guild_id:
            guild = discord.Object(id=int(settings.discord_guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        logger.info("NILE Bot connected as %s", self.user)
        self._listener_task = asyncio.create_task(self._listen_events())

    async def _listen_events(self) -> None:
        """Subscribe to Redis events and forward to Discord."""
        if not self.redis:
            return
        pubsub = self.redis.pubsub()
        await pubsub.subscribe("nile:events")
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    event = json.loads(message["data"])
                    await self._route_event(event)
                except Exception:
                    logger.exception("Failed to process event")
        finally:
            await pubsub.unsubscribe("nile:events")
            await pubsub.close()

    async def _route_event(self, event: dict) -> None:
        """Route ecosystem events to appropriate Discord channels."""
        event_type = event.get("event_type", "")
        metadata = event.get("metadata", {})

        # Find the default channel
        for guild in self.guilds:
            channel = discord.utils.get(guild.text_channels, name="nile-feed")
            if not channel:
                # Try creating it
                try:
                    channel = await guild.create_text_channel("nile-feed")
                except discord.Forbidden:
                    channel = guild.system_channel

            if not channel:
                continue

            embed = discord.Embed(
                title=self._event_title(event_type),
                description=self._event_description(event_type, metadata),
                color=self._event_color(event_type),
                timestamp=datetime.now(UTC),
            )

            if metadata:
                for key, value in list(metadata.items())[:5]:
                    embed.add_field(name=key, value=str(value), inline=True)

            await channel.send(embed=embed)

    def _event_title(self, event_type: str) -> str:
        titles = {
            "agent.joined": "New Agent Joined",
            "contribution.detection": "Vulnerability Detected",
            "contribution.patch": "Patch Submitted",
            "contribution.exploit": "Exploit Verified",
            "contribution.verification": "Cross-Verification",
            "contribution.false_positive": "False Positive",
            "scan.completed": "Scan Completed",
            "task.claimed": "Task Claimed",
            "knowledge.pattern_added": "New Pattern Added",
        }
        return titles.get(event_type, event_type)

    def _event_description(self, event_type: str, metadata: dict) -> str:
        if event_type == "agent.joined":
            name = metadata.get("name", "Unknown")
            caps = metadata.get("capabilities", [])
            return f"**{name}** joined with capabilities: {', '.join(caps)}"
        if event_type == "scan.completed":
            score = metadata.get("nile_score", "?")
            grade = metadata.get("grade", "?")
            return f"NILE Score: **{score}** (Grade: {grade})"
        if "contribution" in event_type:
            points = metadata.get("points", 0)
            severity = metadata.get("severity", "")
            sev_text = f" | Severity: {severity}" if severity else ""
            return f"Points awarded: **{points}**{sev_text}"
        return ""

    def _event_color(self, event_type: str) -> int:
        if "joined" in event_type:
            return 0x22C55E  # green
        if "detection" in event_type or "exploit" in event_type:
            return 0xEF4444  # red
        if "patch" in event_type:
            return 0x3B82F6  # blue
        if "false_positive" in event_type:
            return 0xF59E0B  # yellow
        return 0x6366F1  # purple


bot = NileBot()


# --- Slash Commands ---


@bot.tree.command(name="nile-status", description="Current NILE ecosystem stats")
async def nile_status(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="NILE Ecosystem Status",
        color=0x0EA5E9,
        timestamp=datetime.now(UTC),
    )
    embed.add_field(name="Status", value="Online", inline=True)
    embed.add_field(name="Version", value="0.2.0", inline=True)
    embed.set_footer(text="NILE Security Intelligence Platform")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="nile-leaderboard", description="Top agents by points")
async def nile_leaderboard(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="Agent Leaderboard",
        description="Visit the dashboard for full rankings",
        color=0x0EA5E9,
    )
    embed.add_field(
        name="View Full Leaderboard",
        value="[Dashboard](/agents)",
        inline=False,
    )
    await interaction.response.send_message(embed=embed)


def run_bot() -> None:
    """Run the Discord bot."""
    if not settings.discord_token:
        logger.error("NILE_DISCORD_TOKEN not set. Bot will not start.")
        return
    bot.run(settings.discord_token)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bot()
