import logging

from .cog import Leaderboard, leaderboard as leaderboard_command

log = logging.getLogger("ballsdex.packages.leaderboard")

__all__ = ["Leaderboard"]


async def setup(bot) -> None:
    log.info("Loading Leaderboard package...")
    
    cog = Leaderboard(bot)
    await bot.add_cog(cog)
    
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None and hasattr(balls_cog, "balls_slash_name"):
        from settings.models import settings
        getattr(balls_cog, settings.balls_slash_name).add_command(leaderboard_command)
    
    log.info("Leaderboard package loaded successfully!")


async def teardown(bot) -> None:
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None and hasattr(balls_cog, "balls_slash_name"):
        getattr(balls_cog, "balls_slash_name").remove_command("leaderboard")
