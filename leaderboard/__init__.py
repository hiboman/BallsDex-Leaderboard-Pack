import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.leaderboard")

async def setup(bot: "BallsDexBot"):
    log.info("Loading Leaderboard package...")
    from .cog import Leaderboard
    await bot.add_cog(Leaderboard(bot))
    log.info("Leaderboard package loaded successfully!")
