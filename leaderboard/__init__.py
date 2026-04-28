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
        
        # Use the app_command attribute directly
        command_group = balls_cog.app_command
        log.info(f"Command group name: {command_group.name}")
        log.info(f"Command group qualified_name: {command_group.qualified_name}")
        command_group.add_command(cog.leaderboard)
        log.info("Added leaderboard command to app_command group")
    
    log.info("Leaderboard package loaded successfully!")


async def teardown(bot) -> None:
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None:
        balls_cog.app_command.remove_command("leaderboard")
        log.info("Removed leaderboard command from app_command group")
