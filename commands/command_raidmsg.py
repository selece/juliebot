import logging
import os

from twitchio.ext import commands

LOGGER: logging.Logger = logging.getLogger("command_raidmsg")

class CommandRaidMsg(commands.Component):
    def __init__(self) -> None:
        self.raidmsg_message = False if os.environ["COMMAND_RAIDMSG_MSG"] == "" else os.environ["COMMAND_RAIDMSG_MSG"]

    @commands.command(aliases=["raidmsg"])
    @commands.is_elevated()
    async def raidmessage(self, ctx: commands.Context) -> None:
        if self.raidmsg_message:
            await ctx.send(str(self.raidmsg_message))
        else:
            LOGGER.warning("no raid message configured in env; no raid message will be sent to channel")