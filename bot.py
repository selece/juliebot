import os
import logging

from datetime import datetime, timedelta

from db import DB
from cogs.puns import PunsCog
from cogs.songs import SongsCog
from twitchio.ext import commands, routines

logger = logging.getLogger(__name__)
db = DB.instance()

class JulieBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=os.environ['TOKEN'],
            nick=os.environ['BOT_NICK'],
            prefix=os.environ['BOT_PREFIX'],
            initial_channels=[os.environ['CHANNEL']],
        )

        # cogs
        self.add_cog(PunsCog(self))
        self.add_cog(SongsCog(self))

    # message sender
    async def send_message_to_chat(self, message: str):
        for channel in self.connected_channels:
            await channel.send(message)

    # on connect
    async def event_ready(self):
        logger.info(f'logged in as {self.nick} and user id {self.user_id}')

    # message handler
    async def event_message(self, message: str):
        if message.echo:
            return

        await self.handle_commands(message)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)-15s [%(levelname)s] %(funcName)s: %(message)s")
    bot = JulieBot()
    bot.run()