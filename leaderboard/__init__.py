import logging

from .cog import Leaderboard

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
        
        # Try to find the command group
        command_group = None
        group_name = None
        
        # First try the settings name
        if hasattr(balls_cog, settings.balls_slash_name):
            command_group = getattr(balls_cog, settings.balls_slash_name)
            group_name = settings.balls_slash_name
        else:
            # Fall back to "balls" if settings name doesn't exist
            if hasattr(balls_cog, "balls"):
                command_group = getattr(balls_cog, "balls")
                group_name = "balls"
        
        if command_group is not None:
            command_group.add_command(cog.leaderboard)
            log.info(f"Added leaderboard command to {group_name} group")
        else:
            log.error("No command group found in Balls cog!")
    
    log.info("Leaderboard package loaded successfully!")


async def teardown(bot) -> None:
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None:
        from settings.models import settings
        
        # Try to find the command group
        command_group = None
        group_name = None
        
        # First try the settings name
        if hasattr(balls_cog, settings.balls_slash_name):
            command_group = getattr(balls_cog, settings.balls_slash_name)
            group_name = settings.balls_slash_name
        else:
            # Fall back to "balls" if settings name doesn't exist
            if hasattr(balls_cog, "balls"):
                command_group = getattr(balls_cog, "balls")
                group_name = "balls"
        
        if command_group is not None:
            command_group.remove_command("leaderboard")
            log.info(f"Removed leaderboard command from {group_name} group")
