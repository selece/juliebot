import logging
import os

from datetime import datetime, timedelta
from twitchio.ext import commands, routines
from db import DB


logger = logging.getLogger(__name__)
db = DB.instance()

class SongsCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.last_message_was_me = False
        self.last_active_chat_timestamp = datetime.now()

        self.CHAT_INACTIVITY_TIMER = timedelta(minutes=int(os.environ['CHAT_INACTIVITY_TIMER']))
        self.automated_chat_monitor.start()
        self.automated_songbot_helper.start()

    # message sender
    async def send_message_to_chat(self, message: str):
        for channel in self.bot.connected_channels:
            await channel.send(message)

    @commands.Cog.event()
    async def event_message(self, message: str):
        if message.echo:
            self._last_message_was_me = True
            return
        
        else:
            self._last_message_was_me = False
            self._last_active_chat_timestamp = datetime.now()

    # songlist
    @commands.cooldown(rate=1, per=int(os.environ['SONGS_COG_LIST_COMMAND_FREQUENCY']), bucket=commands.Bucket.channel)
    @commands.command(aliases=("list", "sl", "slist"))
    async def songlist(self, ctx: commands.Context):
        await self.send_message_to_chat(f'hey @{ctx.author.name}, here\'s the song list link! {os.environ['SONGS_COG_URL']}')

    # routine definitions
    @routines.routine(minutes=int(os.environ['SONGS_COG_HELPER_MESSAGE_FREQUENCY']), wait_first=True)
    async def automated_songbot_helper(self):
        if not self.last_message_was_me:
            await self.send_message_to_chat(f'song request quickstart: !songlist for a link to a full menu of songs <3')

        else:
            logger.info(f'skipping automated songbot helper; last message was sent by me: {self.last_message_was_me}')

    @routines.routine(minutes=2, wait_first=True)
    async def automated_chat_monitor(self):
        now_timestamp = datetime.now()
        if now_timestamp - self.last_active_chat_timestamp > self.CHAT_INACTIVITY_TIMER:
            pass