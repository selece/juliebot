import logging
import os

from twitchio.ext import commands

LOGGER: logging.Logger = logging.getLogger("basic_channel")

class BasicChannel(commands.Component):
    def __init__(self) -> None:
        self.raidmsg_message = os.environ.get("COMMAND_RAIDMSG_MSG", "")
        self.adbreak_message = os.environ.get("COMMAND_ADBREAK_MSG", "")
        self.songlist_link = os.environ.get("COMMAND_SONGLIST_LINK", "")

        if self.songlist_link:
            LOGGER.info(f"set up !songlist command with link {self.songlist_link}")
        else:
            LOGGER.warning(f"no !songlist link provided, command will not function")

        if self.adbreak_message:
            LOGGER.info(f"set up !adbreak command with message {self.adbreak_message}")
        else:
            LOGGER.warning(f"no !adbreak message provided, command will not function")

        if self.raidmsg_message:
            LOGGER.info(f"set up !raidmessage command with message {self.raidmsg_message}")
        else:
            LOGGER.warning(f"no !raidmessage message provided, command will not function")

    @commands.command(aliases=["raidmsg"])
    @commands.is_elevated()
    async def raidmessage(self, ctx: commands.Context) -> None:
        if self.raidmsg_message:
            await ctx.send(str(self.raidmsg_message))

    @commands.command(aliases=["break", "ad"])
    @commands.is_elevated()
    async def adbreak(self, ctx: commands.Context) -> None:
        if self.adbreak_message:
            await ctx.send(str(self.adbreak_message))

    @commands.command(aliases=["songs", "sl", "list", "song"])
    @commands.cooldown(rate=1, per=60, key=commands.BucketType.channel)
    async def songlist(self, ctx: commands.Context) -> None:
        if self.songlist_link:
            await ctx.reply(f"here's the song list link! {self.songlist_link}")
