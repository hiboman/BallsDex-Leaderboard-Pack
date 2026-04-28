from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import discord
from asgiref.sync import sync_to_async
from discord import app_commands
from discord.ext import commands
from django.db.models import Count, Q

from bd_models.models import Player
from ballsdex.core.utils.transformers import BallEnabledTransform, SpecialEnabledTransform
from settings.models import settings

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.leaderboard")

# Configuration constants
TOP_PLAYER_LIMIT = [10, 20] # MIN, MAX
ITEMS_PER_PAGE = 5 # How many players are shown on a page
EXCLUDE_IDS = [] # A comma seperated list of User ID's to exclude from the leaderboard
EXCLUDE_BOTS = True # Whether to exclude bots from the leaderboard

class LeaderboardView(discord.ui.LayoutView):
    def __init__(
        self,
        bot: "BallsDexBot",
        interaction: discord.Interaction,
        entries: list[dict[str, Any]],
        subtitle: str,
        value_name: str,
        *,
        suffix: str = "",
    ):
        super().__init__(timeout=120)
        self.bot = bot
        self.interaction = interaction
        self.entries = entries
        self.subtitle = subtitle
        self.value_name = value_name
        self.suffix = suffix
        self.page = 0
        self.per_page = ITEMS_PER_PAGE
        self.disabled = False
        self.message = None
        self.render_page()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("You cannot use this leaderboard.", ephemeral=True)
            return False
        return True

    def max_pages(self) -> int:
        return max(1, (len(self.entries) - 1) // self.per_page + 1)

    async def first(self, interaction: discord.Interaction):
        self.page = 0
        self.render_page()
        await interaction.response.edit_message(view=self)

    async def previous(self, interaction: discord.Interaction):
        self.page = max(0, self.page - 1)
        self.render_page()
        await interaction.response.edit_message(view=self)

    async def next(self, interaction: discord.Interaction):
        self.page = min(self.max_pages() - 1, self.page + 1)
        self.render_page()
        await interaction.response.edit_message(view=self)

    async def last(self, interaction: discord.Interaction):
        self.page = self.max_pages() - 1
        self.render_page()
        await interaction.response.edit_message(view=self)

    async def quit(self, interaction: discord.Interaction):
        self.disabled = True
        self.render_page()
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        self.disabled = True
        self.render_page()
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

    def render_page(self) -> None:
        self.clear_items()

        bot_user = self.interaction.client.user
        header_kwargs: dict[str, Any] = {}
        if bot_user is not None:
            header_kwargs["accessory"] = discord.ui.Thumbnail(media=bot_user.display_avatar.url)

        header = discord.ui.Section(
            discord.ui.TextDisplay(content=f"# {settings.bot_name} Leaderboard"),
            discord.ui.TextDisplay(content=self.subtitle),
            **header_kwargs,
        )
        container = discord.ui.Container(
            header,
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
        )

        start = self.page * self.per_page
        end = start + self.per_page
        for entry in self.entries[start:end]:
            rank = entry["rank"]
            user = entry["user"]
            discord_id = entry["discord_id"]
            count = entry["count"]
            if user is None:
                name = f"Unknown User ({discord_id})"
                thumb = bot_user.display_avatar.url if bot_user is not None else None
            else:
                name = user.name
                thumb = user.display_avatar.url

            section_kwargs: dict[str, Any] = {}
            if thumb is not None:
                section_kwargs["accessory"] = discord.ui.Thumbnail(media=thumb)

            suffix = f"{self.suffix}" if self.suffix else ""
            value_text = f"{count:,} {self.value_name}"
            if suffix:
                value_text = f"{value_text} {suffix}"
            container.add_item(
                discord.ui.Section(
                    discord.ui.TextDisplay(
                        content=f"{rank}. **{name}**\n{value_text}"
                    ),
                    **section_kwargs,
                )
            )

        first = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="<<",
            disabled=self.disabled or self.page == 0,
        )
        back = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Back",
            disabled=self.disabled or self.page == 0,
        )
        nxt = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Next",
            disabled=self.disabled or self.page >= self.max_pages() - 1,
        )
        last = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label=">>",
            disabled=self.disabled or self.page >= self.max_pages() - 1,
        )
        quit_btn = discord.ui.Button(
            style=discord.ButtonStyle.red,
            label="Quit",
            disabled=self.disabled,
        )

        first.callback = self.first
        back.callback = self.previous
        nxt.callback = self.next
        last.callback = self.last
        quit_btn.callback = self.quit

        container.add_item(discord.ui.ActionRow(first, back, nxt, last, quit_btn))
        container.add_item(
            discord.ui.TextDisplay(content=f"-# Page {self.page + 1}/{self.max_pages()}")
        )
        self.add_item(container)


class Leaderboard(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    async def send_component_leaderboard(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        players: list[Player],
        subtitle: str,
        value_name: str,
        *,
        value_attr: str = "ball_count",
        suffix: str = "",
    ) -> None:
        async def resolve_user(player: Player) -> dict[str, Any] | None:
            if player.discord_id in EXCLUDE_IDS:
                return None
            user = self.bot.get_user(player.discord_id)
            if user is None:
                try:
                    user = await self.bot.fetch_user(player.discord_id)
                except discord.DiscordException:
                    user = None

            if EXCLUDE_BOTS and getattr(user, "bot", False):
                return None

            return {
                "discord_id": player.discord_id,
                "user": user,
                "count": getattr(player, value_attr),
            }

        results = await asyncio.gather(*(resolve_user(player) for player in players))
        entries = []
        for result in results:
            if result is not None:
                result["rank"] = len(entries) + 1
                entries.append(result)

        if not entries:
            await interaction.followup.send("No players found.", ephemeral=True)
            return

        view = LeaderboardView(
            self.bot,
            interaction,
            entries,
            subtitle=subtitle,
            value_name=value_name,
            suffix=suffix,
        )
        view.message = await interaction.followup.send(view=view)

    @app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
    @app_commands.choices(
        top=[
            app_commands.Choice(name=str(player_limit), value=player_limit)
            for player_limit in TOP_PLAYER_LIMIT
        ]
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        countryball: BallEnabledTransform | None = None,
        special: SpecialEnabledTransform | None = None,
        currency: bool = False,
        server: bool = False,
        top: int = TOP_PLAYER_LIMIT[0],
    ):
        """
        Show the leaderboard of players.

        Parameters
        ----------
        countryball: BallEnabledTransform
            Only count players with this countryball.
        special: SpecialEnabledTransform
            Only count players with this special.
        currency: bool
            Only count players with currency.
        server: bool
            Only count members of the current server.
        top: int
            Number of players to show.
        """
        await interaction.response.defer(thinking=True)

        if currency and (countryball or special):
            await interaction.followup.send(f"Currency and {settings.collectible_name}/special filters are mutually exclusive.", ephemeral=True)
            return
        if currency and not getattr(settings, "currency_name", None):
            await interaction.followup.send("Currency is not enabled on this bot.", ephemeral=True)
            return

        try:
            server_member_ids = None
            player_query = Player.objects.exclude(discord_id__in=EXCLUDE_IDS)
            server_suffix = ""
            use_fallback_filter = False
            if server:
                guild = interaction.guild
                if guild is None:
                    await interaction.followup.send(
                        "The server option can only be used inside a server.",
                        ephemeral=True,
                    )
                    return

                if interaction.client.intents.members:
                    if not guild.chunked:
                        try:
                            await guild.chunk(cache=True)
                        except Exception:
                            log.warning("Could not chunk guild %s (%d)", guild.name, guild.id)

                    server_member_ids = [member.id for member in guild.members]
                    # Fallback to fetch_members if chunking failed to retrieve members
                    if len(server_member_ids) <= 1:
                        try:
                            server_member_ids = [member.id async for member in guild.fetch_members(limit=None)]
                        except Exception:
                            log.exception("Could not fetch members for guild %s (%d)", guild.name, guild.id)
                            server_member_ids = [member.id for member in guild.members]

                    player_query = player_query.filter(discord_id__in=server_member_ids)
                else:
                    use_fallback_filter = True
                server_suffix = "in this server"

            queryset = player_query
            value_attr = "ball_count"
            suffix = ""

            if currency:
                queryset = queryset.order_by("-money")
                subtitle_template = f"Top {{}} richest players {server_suffix}"
                value_name = settings.currency_name
                value_attr = "money"
            elif countryball or special:
                ball_filter = Q()
                title_parts = []
                value_parts = []
                if special:
                    ball_filter &= Q(balls__special_id=special.id)
                    title_parts.append(str(special))
                    value_parts.append(str(special))
                if countryball:
                    ball_filter &= Q(balls__ball=countryball)
                    title_parts.append(str(countryball))
                    value_parts.append(str(countryball))

                queryset = queryset.annotate(
                    ball_count=Count("balls", filter=ball_filter)
                ).order_by("-ball_count")
                label = " ".join(title_parts)
                subtitle_template = f"Top {{}} players with {label}{server_suffix}"
                value_name = " ".join(value_parts)
                suffix = "owned"
            else:
                queryset = queryset.annotate(ball_count=Count("balls")).order_by("-ball_count")
                subtitle_template = f"Top {{}} players {server_suffix}"
                value_name = settings.plural_collectible_name

            if use_fallback_filter:
                server_players = []
                offset = 0
                semaphore = asyncio.Semaphore(10)

                async def check_player(player: Player) -> Player | None:
                    member = guild.get_member(player.discord_id)
                    if member is not None:
                        if EXCLUDE_BOTS and member.bot:
                            return None
                        return player
                    async with semaphore:
                        try:
                            member = await guild.fetch_member(player.discord_id)
                            if EXCLUDE_BOTS and member.bot:
                                return None
                            return player
                        except discord.HTTPException:
                            return None

                cached_ids = [m.id for m in guild.members if not (EXCLUDE_BOTS and m.bot) and m.id not in EXCLUDE_IDS]
                if cached_ids:
                    cached_players = await sync_to_async(lambda: list(queryset.filter(discord_id__in=cached_ids)))()
                    for p in cached_players:
                        if p not in server_players:
                            server_players.append(p)

                while len(server_players) < top and offset < 500:
                    batch_query = queryset[offset : offset + 50]
                    batch = await sync_to_async(list)(batch_query)
                    if not batch:
                        break

                    tasks = [check_player(player) for player in batch]
                    results = await asyncio.gather(*tasks)

                    for p in results:
                        if p is not None and p not in server_players:
                            server_players.append(p)

                    offset += 50

                def get_sort_key(player: Player):
                    return getattr(player, value_attr, 0)

                server_players.sort(key=get_sort_key, reverse=True)
                players = server_players[:top]
            else:
                players = await sync_to_async(
                    lambda: list(queryset[:top])
                )()

            await self.send_component_leaderboard(
                interaction,
                players,
                subtitle=subtitle_template.format(len(players)),
                value_name=value_name,
                value_attr=value_attr,
                suffix=suffix,
            )
        except Exception:
            log.exception("Error building leaderboard")
            await interaction.followup.send(
                "An error occurred while fetching the leaderboard. Please try again later.",
                ephemeral=True,
            )
