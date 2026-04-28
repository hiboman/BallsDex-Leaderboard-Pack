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
        group_name = settings.balls_slash_name
        log.info(f"Group name: {group_name}")
        log.info(f"Has attribute {group_name}: {hasattr(balls_cog, group_name)}")
        
        if hasattr(balls_cog, group_name):
            group = getattr(balls_cog, group_name)
            log.info(f"Group found: {group}")
            log.info(f"Group type: {type(group)}")
            log.info(f"Adding leaderboard command...")
            group.add_command(leaderboard_command)
            log.info("Leaderboard command added successfully!")
        else:
            log.error(f"Balls cog found but no '{group_name}' attribute")
            log.info(f"Available attributes: {[attr for attr in dir(balls_cog) if not attr.startswith('_')]}")
    else:
        log.error("Balls cog not found!")
        log.info(f"Available cogs: {list(bot.cogs.keys())}")
    
    log.info("Leaderboard package loaded successfully!")


async def teardown(bot) -> None:
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None and hasattr(balls_cog, "balls_slash_name"):
        getattr(balls_cog, "balls_slash_name").remove_command("leaderboard")
