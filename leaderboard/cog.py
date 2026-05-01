import logging
from typing import TYPE_CHECKING, List

import discord
from bd_models.models import Player
from discord import app_commands
from discord.ext import commands
from django.db.models import Count
from settings.models import settings

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.leaderboard")


class LeaderboardPaginator(discord.ui.LayoutView):
    """A Components v2 paginator for leaderboard pages."""

    page_display = discord.ui.TextDisplay("")
    controls = discord.ui.ActionRow()

    def __init__(self, pages: List[str], user_id: int):
        super().__init__(timeout=180)
        self.pages = pages
        self.user_id = user_id
        self.page = 0
        self.message = None
        self.sync_state()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "You cannot use this button.", ephemeral=True
            )
            return False
        return True

    def sync_state(self):
        """Update the displayed page and button states."""
        self.page_display.content = self.pages[self.page]
        self.first_page.disabled = self.page == 0
        self.prev_page.disabled = self.page == 0
        self.next_page.disabled = self.page == len(self.pages) - 1
        self.last_page.disabled = self.page == len(self.pages) - 1

    async def on_timeout(self):
        for item in self.walk_children():
            if hasattr(item, "disabled"):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
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
        for item in self.walk_children():
            if hasattr(item, "disabled"):
                item.disabled = True
        self.stop()
        await interaction.response.edit_message(view=self)


class Leaderboard(commands.Cog):
    """
    Leaderboard cog
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @staticmethod
    def format_page(
        page_players: List[tuple[int, discord.User | str, int]],
        page_number: int,
        total_pages: int,
        heading_count: int,
        collectible_name: str,
    ) -> str:
        lines = [f"# Top {heading_count} Players", ""]

        for rank, user, ball_count in page_players:
            if isinstance(user, str):
                display_name = user
            else:
                display_name = getattr(user, "display_name", None) or user.name
            display_name = discord.utils.escape_markdown(display_name)
            lines.append(f"**{rank}. {display_name}**")
            lines.append(f"{collectible_name}: {ball_count}")
            lines.append("")

        lines.append(f"*Page {page_number}/{total_pages}*")
        return "\n".join(lines).strip()

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

            top_count = top.value if top else 10

            query = Player.objects.annotate(ball_count=Count("balls")).order_by(
                "-ball_count"
            )[:top_count]

            players = []
            rank = 1
            async for player in query:
                user = interaction.client.get_user(player.discord_id)
                if user is None:
                    try:
                        user = await interaction.client.fetch_user(player.discord_id)
                    except Exception:
                        user = f"Unknown User ({player.discord_id})"
                players.append((rank, user, player.ball_count))
                rank += 1

            if not players:
                await interaction.followup.send("No players found.", ephemeral=True)
                return

            players_per_page = 5
            total_pages = (len(players) + players_per_page - 1) // players_per_page
            heading_count = min(top_count, len(players))
            collectible_name = settings.plural_collectible_name.title()
            pages = []

            for page in range(total_pages):
                start_idx = page * players_per_page
                end_idx = start_idx + players_per_page
                page_players = players[start_idx:end_idx]
                pages.append(
                    self.format_page(
                        page_players=page_players,
                        page_number=page + 1,
                        total_pages=total_pages,
                        heading_count=heading_count,
                        collectible_name=collectible_name,
                    )
                )

            if len(pages) == 1:
                await interaction.followup.send(content=pages[0])
            else:
                view = LeaderboardPaginator(pages, interaction.user.id)
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
