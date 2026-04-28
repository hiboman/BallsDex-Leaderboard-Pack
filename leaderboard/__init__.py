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
        
        # Check what attributes actually exist
        available_attrs = [attr for attr in dir(balls_cog) if not attr.startswith('_')]
        log.info(f"Available attributes: {available_attrs}")
        
        # Try to find the command group
        command_group = None
        for attr in available_attrs:
            attr_obj = getattr(balls_cog, attr)
            if hasattr(attr_obj, 'add_command'):
                command_group = attr_obj
                log.info(f"Found command group: {attr}")
                break
        
        if command_group is not None:
            log.info(f"Adding leaderboard command to {attr} group")
            command_group.add_command(leaderboard_command)
            log.info("Leaderboard command added successfully!")
        else:
            log.error("No command group found in Balls cog!")
            log.error(f"Available attributes: {available_attrs}")
    else:
        log.error("Balls cog not found!")
        log.info(f"Available cogs: {list(bot.cogs.keys())}")
    else:
        log.error("Balls cog not found!")
        log.info(f"Available cogs: {list(bot.cogs.keys())}")
    
    log.info("Leaderboard package loaded successfully!")


async def teardown(bot) -> None:
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None:
        # Find the command group dynamically
        available_attrs = [attr for attr in dir(balls_cog) if not attr.startswith('_')]
        for attr in available_attrs:
            attr_obj = getattr(balls_cog, attr)
            if hasattr(attr_obj, 'remove_command'):
                attr_obj.remove_command("leaderboard")
                log.info(f"Removed leaderboard command from {attr} group")
                break
