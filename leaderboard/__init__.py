import logging

from .cog import Leaderboard

log = logging.getLogger("ballsdex.packages.leaderboard")

__all__ = ["Leaderboard"]


async def setup(bot) -> None:
    log.info("Loading Leaderboard package...")

    cog = Leaderboard(bot)
    await bot.add_cog(cog)
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None:
        from settings.models import settings

        command_group = balls_cog.app_command
        command_group.add_command(cog.leaderboard)

    log.info("Leaderboard package loaded successfully!")


async def teardown(bot: "BallsDexBot"):
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None:
        command_group = balls_cog.app_command
        command_group.remove_command("leaderboard")
