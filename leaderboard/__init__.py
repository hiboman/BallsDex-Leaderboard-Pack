import logging

from .cog import Leaderboard
from .cog import leaderboard as leaderboard_command

log = logging.getLogger("ballsdex.packages.leaderboard")

__all__ = ["Leaderboard"]


async def setup(bot) -> None:
    log.info("Loading Leaderboard package...")
    
    cog = Leaderboard(bot)
    await bot.add_cog(cog)
    
    balls_cog = bot.cogs.get("Balls")
    log.info(f"Balls cog found: {balls_cog is not None}")
    
    if balls_cog is not None:
        from settings.models import settings
        
        getattr(balls_cog, settings.balls_slash_name).add_command(leaderboard_command)
        log.info(f"Added leaderboard command to {settings.balls_slash_name} group")
    
    log.info("Leaderboard package loaded successfully!")


async def teardown(bot) -> None:
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None:
        getattr(balls_cog, settings.balls_slash_name).remove_command("leaderboard")
        log.info(f"Removed leaderboard command from {settings.balls_slash_name} group")
