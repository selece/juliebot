import logging
import os

from datetime import datetime, timedelta
from twitchio.ext import commands, routines
from twitchio.message import Message
from db import DB


logger = logging.getLogger(__name__)
db = DB.instance()

# to access these in decorators, they have to not be inside the class scope
config_vars = {
    "bot_nick": os.environ['BOT_NICK'],
    "songlist_frequency": int(os.environ['SONGS_COG_LIST_COMMAND_FREQUENCY']),
    "helper_message_frequency": int(os.environ['SONGS_COG_HELPER_MESSAGE_FREQUENCY']),
}

class SongsCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.last_message_was_me = False

        self.automated_songbot_helper.start()

    # message sender
    async def send_message_to_chat(self, message: str) -> None:
        for channel in self.bot.connected_channels:
            await channel.send(message)

    @commands.Cog.event()
    async def event_message(self, message: Message) -> None:
        return

    # songlist
    @commands.cooldown(rate=1, per=config_vars["songlist_frequency"], bucket=commands.Bucket.channel)
    @commands.command(aliases=("list", "sl", "slist"))
    async def songlist(self, ctx: commands.Context) -> None:
        await self.send_message_to_chat(f'hey @{ctx.author.name}, here\'s the song list link! {os.environ['SONGS_COG_URL']}')

    # routine definitions
    @routines.routine(minutes=config_vars["helper_message_frequency"], wait_first=False)
    async def automated_songbot_helper(self) -> None:
        await self.send_message_to_chat(f'song request quickstart: !list for a link to a full menu of songs <3')
