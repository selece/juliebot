import logging
import os

from twitchio.ext import commands

LOGGER: logging.Logger = logging.getLogger("command_adbreak")

class CommandAdbreak(commands.Component):
    def __init__(self) -> None:
        self.adbreak_message = os.environ.get("COMMAND_ADBREAK_MSG", "")

    @commands.command(aliases=["break", "ad"])
    @commands.is_elevated()
    async def adbreak(self, ctx: commands.Context) -> None:
        if self.adbreak_message:
            await ctx.send(str(self.adbreak_message))
        else:
            LOGGER.warning("no adbreak message configured in env; no adbreak message will be sent to channel")