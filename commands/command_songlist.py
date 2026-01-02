import logging
import os

from twitchio.ext import commands

LOGGER: logging.Logger = logging.getLogger("command_songlist")

class CommandSongList(commands.Component):
    def __init__(self) -> None:
        self.songlist_link = False if os.environ["COMMAND_SONGLIST_LINK"] == "" else os.environ["COMMAND_SONGLIST_LINK"]
        LOGGER.info(f"set up songlist command with link {self.songlist_link}")

    @commands.command(aliases=["songs", "sl", "list", "song"])
    @commands.cooldown(rate=1, per=60, key=commands.BucketType.channel)
    async def songlist(self, ctx: commands.Context) -> None:
        if self.songlist_link:
            await ctx.reply(f"here's the song list link! {self.songlist_link}")
        else:
            LOGGER.warning("No songlist link configured in env; no response will be sent to chat for this command.")
