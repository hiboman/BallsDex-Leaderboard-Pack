import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.leaderboard")

async def setup(bot: "BallsDexBot"):
    log.info("Loading Leaderboard package...")
    from .cog import Leaderboard
    
    # Add the cog
    cog = Leaderboard(bot)
    await bot.add_cog(cog)
    
    # Hook into the existing /balls command group
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None and hasattr(balls_cog, "balls"):
        # Remove the existing leaderboard command if it exists
        if hasattr(balls_cog.balls, "leaderboard"):
            balls_cog.balls.remove_command("leaderboard")
        
        # Add our leaderboard command
        from .cog import leaderboard
        balls_cog.balls.add_command(leaderboard)
    
    log.info("Leaderboard package loaded successfully!")

async def teardown(bot: "BallsDexBot"):
    # Remove our leaderboard command from /balls group
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None and hasattr(balls_cog, "balls"):
        if hasattr(balls_cog.balls, "leaderboard"):
            balls_cog.balls.remove_command("leaderboard")
