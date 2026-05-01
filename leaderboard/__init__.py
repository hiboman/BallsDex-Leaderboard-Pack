import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.leaderboard")


async def setup(bot: "BallsDexBot"):
    log.info("Loading Leaderboard package...")
    from .cog import Leaderboard

    cog = Leaderboard(bot)
    await bot.add_cog(cog)
    bot.tree.remove_command("leaderboard")
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None:
        command_group = balls_cog.app_command
        if command_group is None:
            log.warning(
                "Balls cog app command group is unavailable; skipping registration."
            )
        elif command_group.get_command("leaderboard") is None:
            command_group.add_command(cog.leaderboard)
        else:
            log.warning(
                "Leaderboard command is already registered; skipping duplicate."
            )
    else:
        log.warning("Balls cog was not found; leaderboard command was not registered.")

    log.info("Leaderboard package loaded successfully!")


async def teardown(bot: "BallsDexBot"):
    bot.tree.remove_command("leaderboard")
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None:
        command_group = balls_cog.app_command
        if (
            command_group is not None
            and command_group.get_command("leaderboard") is not None
        ):
            command_group.remove_command("leaderboard")
