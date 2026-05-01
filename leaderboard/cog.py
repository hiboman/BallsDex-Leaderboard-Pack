import logging
from typing import TYPE_CHECKING, List, TypeAlias

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.leaderboard")

LeaderboardEntry: TypeAlias = tuple[int, str, int, str | None]


class LeaderboardPaginator(discord.ui.LayoutView):
    """A Components v2 paginator for leaderboard pages."""

    card = discord.ui.Container(accent_color=discord.Color.blurple())
    controls = discord.ui.ActionRow()

    def __init__(
        self,
        pages: List[List[LeaderboardEntry]],
        user_id: int,
        heading_count: int,
        collectible_name: str,
        total_players: int,
    ):
        super().__init__(timeout=180)
        self.pages = pages
        self.user_id = user_id
        self.heading_count = heading_count
        self.collectible_name = collectible_name
        self.total_players = total_players
        self.page = 0
        self.message = None
        self.sync_state()

    def disable_controls(self) -> None:
        for item in self.walk_children():
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "You cannot use this button.", ephemeral=True
            )
            return False
        return True

    def sync_state(self):
        """Update the displayed page card and button states."""
        self.card.clear_items()
        self.card.add_item(
            discord.ui.TextDisplay(f"## Top {self.heading_count} Players")
        )
        self.card.add_item(
            discord.ui.TextDisplay(
                f"**Tracked Players:** {self.total_players} • **Page:** {self.page + 1}/{len(self.pages)}"
            )
        )
        self.card.add_item(discord.ui.Separator())

        page_entries = self.pages[self.page]
        for index, (rank, display_name, ball_count, avatar_url) in enumerate(
            page_entries
        ):
            accessory: discord.ui.Thumbnail | discord.ui.Button
            if avatar_url:
                accessory = discord.ui.Thumbnail(
                    avatar_url,
                    description=f"{display_name}'s avatar",
                )
            else:
                accessory = discord.ui.Button(
                    label=str(rank),
                    style=discord.ButtonStyle.secondary,
                    disabled=True,
                )

            self.card.add_item(
                discord.ui.Section(
                    f"**{rank}. {discord.utils.escape_markdown(display_name)}**",
                    f"{self.collectible_name}: {ball_count}",
                    accessory=accessory,
                )
            )
            if index < len(page_entries) - 1:
                self.card.add_item(discord.ui.Separator())

        self.first_page.disabled = self.page == 0
        self.prev_page.disabled = self.page == 0
        self.next_page.disabled = self.page == len(self.pages) - 1
        self.last_page.disabled = self.page == len(self.pages) - 1

    async def on_timeout(self):
        self.disable_controls()
        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

    @controls.button(label="≪", style=discord.ButtonStyle.secondary)
    async def first_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page = 0
        self.sync_state()
        await interaction.response.edit_message(view=self)

    @controls.button(label="Back", style=discord.ButtonStyle.primary)
    async def prev_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page = max(0, self.page - 1)
        self.sync_state()
        await interaction.response.edit_message(view=self)

    @controls.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page = min(len(self.pages) - 1, self.page + 1)
        self.sync_state()
        await interaction.response.edit_message(view=self)

    @controls.button(label="≫", style=discord.ButtonStyle.secondary)
    async def last_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page = len(self.pages) - 1
        self.sync_state()
        await interaction.response.edit_message(view=self)

    @controls.button(label="Quit", style=discord.ButtonStyle.danger)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.disable_controls()
        self.stop()
        await interaction.response.edit_message(view=self)


class Leaderboard(commands.Cog):
    """
    Leaderboard cog
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @staticmethod
    def resolve_stored_player_name(player) -> str | None:
        for attr_name in ("username", "name", "player_name", "display_name"):
            value = getattr(player, attr_name, None)
            if isinstance(value, str):
                value = value.strip()
                if value:
                    return value
        return None

    async def resolve_player_identity(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        player,
        cache: dict[int, tuple[str, str | None]],
    ) -> tuple[str, str | None]:
        discord_id = player.discord_id
        cached_identity = cache.get(discord_id)
        if cached_identity is not None:
            return cached_identity

        stored_name = self.resolve_stored_player_name(player)

        if interaction.guild is not None:
            member = interaction.guild.get_member(discord_id)
            if member is not None:
                identity = (
                    stored_name or member.name,
                    member.display_avatar.url,
                )
                cache[discord_id] = identity
                return identity
            try:
                member = await interaction.guild.fetch_member(discord_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                member = None
            if member is not None:
                identity = (
                    stored_name or member.name,
                    member.display_avatar.url,
                )
                cache[discord_id] = identity
                return identity

        user = interaction.client.get_user(discord_id)
        if user is not None:
            identity = (
                stored_name or user.name,
                user.display_avatar.url,
            )
            cache[discord_id] = identity
            return identity

        try:
            user = await interaction.client.fetch_user(discord_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            user = None
        if user is not None:
            identity = (
                stored_name or user.name,
                user.display_avatar.url,
            )
            cache[discord_id] = identity
            return identity

        identity = (
            stored_name or f"Unknown User ({discord_id})",
            None,
        )
        cache[discord_id] = identity
        return identity

    @staticmethod
    def format_page(
        page_players: List[LeaderboardEntry],
    ) -> List[LeaderboardEntry]:
        return page_players

    @app_commands.command()
    @app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
    @app_commands.choices(
        top=[
            app_commands.Choice(name="10", value=10),
            app_commands.Choice(name="20", value=20),
        ]
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        top: app_commands.Choice[int] | None = None,
    ):
        """
        Show the leaderboard of players with the most caught countryballs.

        Parameters
        ----------
        top: app_commands.Choice[int]
            Number of players to show
        """
        try:
            await interaction.response.defer(thinking=True)
            from bd_models.models import Player
            from django.db.models import Count
            from settings.models import settings

            top_count = top.value if top else 10

            query = Player.objects.annotate(ball_count=Count("balls")).order_by(
                "-ball_count"
            )[:top_count]

            players = []
            identity_cache: dict[int, tuple[str, str | None]] = {}
            rank = 1
            async for player in query:
                display_name, avatar_url = await self.resolve_player_identity(
                    interaction, player, identity_cache
                )
                players.append((rank, display_name, player.ball_count, avatar_url))
                rank += 1

            if not players:
                await interaction.followup.send("No players found.", ephemeral=True)
                return

            players_per_page = 5
            total_pages = (len(players) + players_per_page - 1) // players_per_page
            heading_count = min(top_count, len(players))
            collectible_name = settings.plural_collectible_name.title()
            pages: List[List[LeaderboardEntry]] = []

            for page in range(total_pages):
                start_idx = page * players_per_page
                end_idx = start_idx + players_per_page
                page_players = players[start_idx:end_idx]
                pages.append(
                    self.format_page(
                        page_players=page_players,
                    )
                )

            view = LeaderboardPaginator(
                pages=pages,
                user_id=interaction.user.id,
                heading_count=heading_count,
                collectible_name=collectible_name,
                total_players=len(players),
            )
            if len(pages) == 1:
                view.disable_controls()
            view.message = await interaction.followup.send(view=view, wait=True)

        except Exception as e:
            log.error(f"Error in leaderboard command: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    "An error occurred while fetching the leaderboard. Please try again later.",
                    ephemeral=True,
                )
            except Exception as followup_error:
                log.error(f"Failed to send error message to user: {followup_error}")
