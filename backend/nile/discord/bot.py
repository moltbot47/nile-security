"""NILE Discord bot — real-time research layer for the ecosystem.

Connects to guild 1469930844561871034, creates dedicated channels,
posts ecosystem events and browser screenshots of dashboard pages.
"""

import asyncio
import contextlib
import json
import logging
from datetime import UTC, datetime

import discord
import redis.asyncio as aioredis
from discord import app_commands

from nile.config import settings
from nile.discord.screenshots import DASHBOARD_PAGES, capture_all_pages, capture_page

logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True

# Dashboard URL for screenshots (inside Docker network)
DASHBOARD_URL = "http://frontend:3000"

# Category name for all NILE channels
NILE_CATEGORY = "NILE Security"

# Channels the bot manages
MANAGED_CHANNELS = [
    "nile-feed",
    "nile-dashboard",
    "nile-ecosystem",
    "nile-agents",
    "nile-attacker",
    "nile-defender",
    "nile-alerts",
]

# How often to post fresh screenshots (seconds)
SCREENSHOT_INTERVAL = 3600  # every hour


class NileBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.redis: aioredis.Redis | None = None
        self._listener_task: asyncio.Task | None = None
        self._screenshot_task: asyncio.Task | None = None
        self._target_guild: discord.Guild | None = None
        self._channels: dict[str, discord.TextChannel] = {}

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

        # Find target guild
        guild_id = int(settings.discord_guild_id) if settings.discord_guild_id else None
        if guild_id:
            self._target_guild = self.get_guild(guild_id)
        if not self._target_guild and self.guilds:
            self._target_guild = self.guilds[0]

        if not self._target_guild:
            logger.error("Bot is not in any guild!")
            return

        logger.info("Target guild: %s (%s)", self._target_guild.name, self._target_guild.id)

        # Set up channels
        await self._ensure_channels()

        # Post startup message
        feed = self._channels.get("nile-feed")
        if feed:
            try:
                embed = discord.Embed(
                    title="NILE Security Intelligence — Online",
                    description=(
                        "Agent ecosystem monitoring active.\n"
                        "Dashboard: http://159.203.138.96\n\n"
                        "Channels created for live updates, screenshots, "
                        "and alerts."
                    ),
                    color=0x0EA5E9,
                    timestamp=datetime.now(UTC),
                )
                embed.set_footer(text="NILE v0.2.0")
                await feed.send(embed=embed)
            except discord.Forbidden:
                logger.warning("Cannot send to #nile-feed — missing Send Messages")

        # Start background tasks
        self._listener_task = asyncio.create_task(self._listen_events())
        self._screenshot_task = asyncio.create_task(self._screenshot_loop())

    async def _ensure_channels(self) -> None:
        """Create NILE category and channels if they don't exist."""
        guild = self._target_guild
        if not guild:
            return

        # Find or create category
        category = discord.utils.get(guild.categories, name=NILE_CATEGORY)
        if not category:
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(
                        read_messages=True, send_messages=False
                    ),
                    guild.me: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True,
                        manage_channels=True,
                    ),
                }
                category = await guild.create_category(
                    NILE_CATEGORY,
                    overwrites=overwrites,
                    reason="NILE Security Intelligence Platform",
                )
                logger.info("Created category: %s", NILE_CATEGORY)
            except discord.Forbidden:
                logger.warning("Cannot create category — missing permissions")
                category = None
        # Create managed channels (with bot permissions in overwrites)
        bot_overwrites = {
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
            ),
        }
        for channel_name in MANAGED_CHANNELS:
            existing = discord.utils.get(guild.text_channels, name=channel_name)
            if existing:
                self._channels[channel_name] = existing
                # Try to ensure we can send (ignore if no Manage Roles)
                with contextlib.suppress(discord.Forbidden):
                    await existing.set_permissions(
                        guild.me,
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True,
                    )
            else:
                try:
                    topic = self._channel_topic(channel_name)
                    ch = await guild.create_text_channel(
                        channel_name,
                        category=category,
                        topic=topic,
                        overwrites=bot_overwrites,
                        reason="NILE bot auto-created",
                    )
                    self._channels[channel_name] = ch
                    logger.info("Created channel: #%s", channel_name)
                except discord.Forbidden:
                    logger.warning("Cannot create #%s", channel_name)

    def _channel_topic(self, name: str) -> str:
        topics = {
            "nile-feed": "Live ecosystem events — agents joining, vulns detected, patches verified",
            "nile-dashboard": "Dashboard overview screenshots — updated hourly",
            "nile-ecosystem": "Agent network graph screenshots — live ecosystem view",
            "nile-agents": "Agent leaderboard screenshots — top agents by NILE score",
            "nile-attacker": "Attacker KPI screenshots — exploit success, attack vectors",
            "nile-defender": "Defender KPI screenshots — detection recall, patch rates",
            "nile-alerts": "Critical security alerts — high severity findings",
        }
        return topics.get(name, "NILE Security")

    # --- Event Listener ---

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
        """Route ecosystem events to the right Discord channel."""
        event_type = event.get("event_type", "")
        metadata = event.get("metadata", {})

        # Soul Token market events get special handling
        if event_type.startswith("soul."):
            await self._handle_soul_event(event_type, metadata)
            return

        # Determine target channel
        if "critical" in str(metadata.get("severity", "")):
            channel_name = "nile-alerts"
        else:
            channel_name = "nile-feed"

        channel = self._channels.get(channel_name)
        if not channel:
            return

        embed = discord.Embed(
            title=self._event_title(event_type),
            description=self._event_description(event_type, metadata),
            color=self._event_color(event_type),
            timestamp=datetime.now(UTC),
        )

        if metadata:
            for key, value in list(metadata.items())[:5]:
                embed.add_field(name=key, value=str(value), inline=True)

        embed.set_footer(text=f"Event: {event_type}")
        await channel.send(embed=embed)

        # On significant events, capture a fresh screenshot
        if event_type in ("scan.completed", "agent.joined"):
            asyncio.create_task(self._post_screenshot_to("nile-dashboard", "/", "dashboard"))

    async def _handle_soul_event(self, event_type: str, metadata: dict) -> None:
        """Handle Soul Token market events with rich embeds."""
        if event_type == "soul.risk_alert":
            await self._post_risk_alert(metadata)
        elif event_type == "soul.token_graduated":
            await self._post_graduation(metadata)
        elif event_type == "soul.oracle_confirmed":
            await self._post_oracle_confirmed(metadata)
        elif event_type == "soul.oracle_report_pending":
            await self._post_oracle_pending(metadata)
        elif event_type == "soul.valuation_changed":
            await self._post_valuation_change(metadata)
        else:
            # Generic soul event to feed
            channel = self._channels.get("nile-feed")
            if channel:
                embed = discord.Embed(
                    title=f"Soul Event: {event_type.replace('soul.', '')}",
                    color=0x6366F1,
                    timestamp=datetime.now(UTC),
                )
                for k, v in list(metadata.items())[:6]:
                    embed.add_field(name=k, value=str(v), inline=True)
                await channel.send(embed=embed)

    async def _post_risk_alert(self, m: dict) -> None:
        """Post risk alert to #nile-alerts with severity-coded embed."""
        channel = self._channels.get("nile-alerts")
        if not channel:
            return

        severity = m.get("severity", "warning")
        risk_type = m.get("risk_type", "unknown")
        color = 0xDC2626 if severity == "critical" else 0xF59E0B

        embed = discord.Embed(
            title=f"RISK ALERT: {risk_type.replace('_', ' ').upper()}",
            description=(
                f"**Severity:** {severity.upper()}\n"
                f"**Token:** {m.get('token_id', 'N/A')}\n"
                f"**Action:** {m.get('action', 'N/A')}"
            ),
            color=color,
            timestamp=datetime.now(UTC),
        )
        if m.get("pause_minutes"):
            embed.add_field(
                name="Circuit Breaker",
                value=f"Trading paused for {m['pause_minutes']} minutes",
                inline=False,
            )
        details = m.get("details", {})
        for k, v in list(details.items())[:4]:
            embed.add_field(name=k, value=str(v), inline=True)
        embed.set_footer(text="NILE Risk Engine")
        await channel.send(embed=embed)

    async def _post_graduation(self, m: dict) -> None:
        """Post graduation celebration to #nile-feed."""
        channel = self._channels.get("nile-feed")
        if not channel:
            return

        symbol = m.get("token_symbol", "???")
        reserve = m.get("reserve_eth", 0)
        embed = discord.Embed(
            title=f"${symbol} GRADUATED!",
            description=(
                f"Token **${symbol}** has graduated from bonding curve "
                f"to AMM with **{reserve:.2f} ETH** in reserve.\n\n"
                f"Liquidity deployed to Uniswap V3. LP tokens burned "
                f"for permanent, unruggable liquidity."
            ),
            color=0x22C55E,
            timestamp=datetime.now(UTC),
        )
        embed.set_footer(text="NILE Soul Token Market")
        await channel.send(embed=embed)

    async def _post_oracle_confirmed(self, m: dict) -> None:
        """Post confirmed oracle event to #nile-feed."""
        channel = self._channels.get("nile-feed")
        if not channel:
            return

        embed = discord.Embed(
            title="Oracle Event Confirmed",
            description=(
                f"**Person:** {m.get('person_id', 'N/A')}\n"
                f"**Impact:** {m.get('impact_score', 0):+d}\n"
                f"**Type:** {m.get('event_type', 'N/A')}\n"
                f"Valuation re-computation triggered."
            ),
            color=0x3B82F6,
            timestamp=datetime.now(UTC),
        )
        embed.set_footer(text="NILE Oracle Network")
        await channel.send(embed=embed)

    async def _post_oracle_pending(self, m: dict) -> None:
        """Post pending oracle report for cross-verification."""
        channel = self._channels.get("nile-feed")
        if not channel:
            return

        headline = m.get("headline", "")
        embed = discord.Embed(
            title="New Oracle Report — Awaiting Verification",
            description=(
                f"**{headline[:200]}**\n\n"
                f"Source: {m.get('source', 'N/A')}\n"
                f"Oracle agents: please cross-verify."
            ),
            color=0xF59E0B,
            timestamp=datetime.now(UTC),
        )
        embed.set_footer(text="NILE Oracle Network")
        await channel.send(embed=embed)

    async def _post_valuation_change(self, m: dict) -> None:
        """Post significant valuation change to #nile-feed."""
        channel = self._channels.get("nile-feed")
        if not channel:
            return

        old_s = m.get("old_score", 0)
        new_s = m.get("new_score", 0)
        change = m.get("change_pct", 0)
        direction = "up" if new_s > old_s else "down"
        color = 0x22C55E if direction == "up" else 0xEF4444

        embed = discord.Embed(
            title=f"Valuation Update ({direction.upper()} {change:.1f}%)",
            description=(
                f"**Person:** {m.get('person_id', 'N/A')}\n"
                f"**Score:** {old_s:.1f} → {new_s:.1f}\n"
                f"**Fair Value:** ${m.get('fair_value_usd', 0):.2f}\n"
                f"Market makers alerted to adjust spreads."
            ),
            color=color,
            timestamp=datetime.now(UTC),
        )
        embed.set_footer(text="NILE Valuation Engine")
        await channel.send(embed=embed)

    # --- Screenshot Loop ---

    async def _screenshot_loop(self) -> None:
        """Periodically capture and post dashboard screenshots."""
        # Initial delay — let services warm up
        await asyncio.sleep(30)

        while True:
            try:
                await self._post_all_screenshots()
            except Exception:
                logger.exception("Screenshot loop error")
            await asyncio.sleep(SCREENSHOT_INTERVAL)

    async def _post_all_screenshots(self) -> None:
        """Capture all dashboard pages and post to their channels."""
        logger.info("Capturing dashboard screenshots...")
        screenshots = await capture_all_pages(DASHBOARD_URL)

        for page_info in DASHBOARD_PAGES:
            name = page_info["name"]
            channel_name = page_info["channel"]
            path = screenshots.get(name)

            if path and path.exists():
                channel = self._channels.get(channel_name)
                if channel:
                    embed = discord.Embed(
                        title=f"NILE — {name.replace('-', ' ').title()}",
                        description=f"Live dashboard: http://159.203.138.96{page_info['path']}",
                        color=0x0EA5E9,
                        timestamp=datetime.now(UTC),
                    )
                    file = discord.File(str(path), filename=f"{name}.png")
                    embed.set_image(url=f"attachment://{name}.png")
                    await channel.send(embed=embed, file=file)
                    logger.info("Posted screenshot to #%s", channel_name)

    async def _post_screenshot_to(
        self, channel_name: str, path: str, name: str
    ) -> None:
        """Capture a single page and post to a specific channel."""
        screenshot = await capture_page(DASHBOARD_URL, path, name)
        if screenshot and screenshot.exists():
            channel = self._channels.get(channel_name)
            if channel:
                embed = discord.Embed(
                    title=f"NILE — {name.replace('-', ' ').title()} (Updated)",
                    color=0x0EA5E9,
                    timestamp=datetime.now(UTC),
                )
                file = discord.File(str(screenshot), filename=f"{name}.png")
                embed.set_image(url=f"attachment://{name}.png")
                await channel.send(embed=embed, file=file)

    # --- Helpers ---

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
            "task.created.patch": "Patch Task Created",
            "task.created.exploit": "Exploit Verification Requested",
            "knowledge.pattern_added": "New Pattern Discovered",
            "agent.message": "Agent Communication",
            "soul.risk_alert": "Risk Alert",
            "soul.token_graduated": "Token Graduated",
            "soul.oracle_confirmed": "Oracle Event Confirmed",
            "soul.oracle_report_pending": "Oracle Report Pending",
            "soul.valuation_changed": "Valuation Updated",
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
        return json.dumps(metadata, indent=2)[:200] if metadata else ""

    def _event_color(self, event_type: str) -> int:
        if "joined" in event_type:
            return 0x22C55E
        if "detection" in event_type or "exploit" in event_type:
            return 0xEF4444
        if "patch" in event_type:
            return 0x3B82F6
        if "false_positive" in event_type:
            return 0xF59E0B
        if "alert" in event_type:
            return 0xDC2626
        return 0x6366F1


bot = NileBot()


# --- Slash Commands ---


@bot.tree.command(name="nile-status", description="NILE ecosystem status")
async def nile_status(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="NILE Ecosystem Status",
        color=0x0EA5E9,
        timestamp=datetime.now(UTC),
    )
    embed.add_field(name="Status", value="Online", inline=True)
    embed.add_field(name="Version", value="0.2.0", inline=True)
    embed.add_field(
        name="Dashboard",
        value="[http://159.203.138.96](http://159.203.138.96)",
        inline=False,
    )
    embed.set_footer(text="NILE Security Intelligence Platform")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="nile-screenshot", description="Capture fresh dashboard screenshots")
async def nile_screenshot(interaction: discord.Interaction) -> None:
    await interaction.response.defer(thinking=True)
    screenshots = await capture_all_pages(DASHBOARD_URL)
    count = len(screenshots)
    if count > 0:
        await interaction.followup.send(
            f"Captured {count} screenshots. Check the NILE channels!"
        )
        await bot._post_all_screenshots()
    else:
        await interaction.followup.send(
            "Could not capture screenshots. Playwright may not be installed."
        )


@bot.tree.command(name="nile-leaderboard", description="Top agents by points")
async def nile_leaderboard(interaction: discord.Interaction) -> None:
    await interaction.response.defer()
    screenshot = await capture_page(DASHBOARD_URL, "/agents", "leaderboard")
    if screenshot and screenshot.exists():
        file = discord.File(str(screenshot), filename="leaderboard.png")
        embed = discord.Embed(
            title="Agent Leaderboard",
            description="[View Full Dashboard](http://159.203.138.96/agents)",
            color=0x0EA5E9,
        )
        embed.set_image(url="attachment://leaderboard.png")
        await interaction.followup.send(embed=embed, file=file)
    else:
        embed = discord.Embed(
            title="Agent Leaderboard",
            description="[View on Dashboard](http://159.203.138.96/agents)",
            color=0x0EA5E9,
        )
        await interaction.followup.send(embed=embed)


def run_bot() -> None:
    """Run the Discord bot."""
    if not settings.discord_token:
        logger.error("NILE_DISCORD_TOKEN not set. Bot will not start.")
        return
    bot.run(settings.discord_token)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bot()
