import logging
import os

from twitchio.ext import commands

LOGGER: logging.Logger = logging.getLogger("command_songlist")

class CommandSongList(commands.Component):
    def __init__(self) -> None:
        self.songlist_link = os.environ.get("COMMAND_SONGLIST_LINK", "")

        if self.songlist_link:
            LOGGER.info(f"set up songlist command with link {self.songlist_link}")
        else:
            LOGGER.warning(f"no songlist link provided, command will not function")

    @commands.command(aliases=["songs", "sl", "list", "song"])
    @commands.cooldown(rate=1, per=60, key=commands.BucketType.channel)
    async def songlist(self, ctx: commands.Context) -> None:
        if self.songlist_link:
            await ctx.reply(f"here's the song list link! {self.songlist_link}")
