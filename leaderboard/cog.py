import logging
from typing import TYPE_CHECKING, List

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.leaderboard")

class EmbedPaginator(discord.ui.View):
    """A simple embed paginator for Discord."""

    def __init__(self, embeds: List[discord.Embed], user_id: int, compact: bool = False):
        super().__init__(timeout=180)
        self.embeds = embeds
        self.user_id = user_id
        self.compact = compact
        self.page = 0
        self.message = None
        self.update_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot use this button.", ephemeral=True)
            return False
        return True

    def update_buttons(self):
        """Update button states based on current page."""
        self.first_page.disabled = self.page == 0
        self.prev_page.disabled = self.page == 0
        self.next_page.disabled = self.page == len(self.embeds) - 1
        self.last_page.disabled = self.page == len(self.embeds) - 1

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

    @discord.ui.button(label="≪", style=discord.ButtonStyle.grey)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.blurple)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(len(self.embeds) - 1, self.page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @discord.ui.button(label="≫", style=discord.ButtonStyle.grey)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = len(self.embeds) - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)


class Leaderboard(commands.Cog):
    """
    Leaderboard cog
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @app_commands.command()
    @app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
    @app_commands.choices(top=[
        app_commands.Choice(name="10", value=10),
        app_commands.Choice(name="20", value=20)
    ])
    async def leaderboard(self, interaction: discord.Interaction["BallsDexBot"], top: app_commands.Choice[int] | None = None):
        """
        Show the leaderboard of players with the most caught countryballs.
        
        Parameters
        ----------
        top: app_commands.Choice[int]
            Number of players to show
        """
        try:
            await interaction.response.defer(thinking=True)
            
            from settings.models import settings
            from bd_models.models import Player
            from django.db.models import Count
            
            top_count = top.value if top else 10
            
            query = (
                Player.objects
                .annotate(ball_count=Count("balls"))
                .order_by("-ball_count")[:top_count]
            )

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

            # Create multiple embeds with 5 players per page
            embeds = []
            players_per_page = 5
            total_pages = (top_count + players_per_page - 1) // players_per_page
            
            for page in range(total_pages):
                start_idx = page * players_per_page
                end_idx = start_idx + players_per_page
                page_players = players[start_idx:end_idx]
                
                page_embed = discord.Embed(
                    title=f"Top {top_count} Players",
                    color=discord.Color.blurple()
                )
                
                for rank, user, ball_count in page_players:
                    page_embed.add_field(
                        name=f"**{rank}. {user.name if hasattr(user, 'name') else str(user)}**",
                        value=f"{settings.plural_collectible_name.title()}: {ball_count}",
                        inline=False
                    )
                
                page_embed.set_footer(text=f"Page {page + 1}/{total_pages}")
                embeds.append(page_embed)
            
            if len(embeds) == 1:
                await interaction.followup.send(embed=embeds[0])
            else:
                view = EmbedPaginator(embeds, interaction.user.id, compact=True)
                view.message = await interaction.followup.send(embed=embeds[0], view=view)

        except Exception as e:
            log.error(f"Error in leaderboard command: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    "An error occurred while fetching the leaderboard. Please try again later.",
                    ephemeral=True
                )
            except Exception as followup_error:
                log.error(f"Failed to send error message to user: {followup_error}")
