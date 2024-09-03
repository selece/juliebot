import os
import logging
from twitchio.ext import commands, routines

logger = logging.getLogger(__name__)

class JulieBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=os.environ['TOKEN'],
            nick=os.environ['BOT_NICK'],
            prefix=os.environ['BOT_PREFIX'],
            initial_channels=[os.environ['CHANNEL']],
        )

        # routines 
        for _r in [ self.automated_songbot_helper ]:
            _r.start()

        # vars
        self._last_message_was_me = False

    # message sender
    async def send_message_to_chat(self, message):
        for channel in self.connected_channels:
            await channel.send(message)

    # on connect
    async def event_ready(self):
        logger.info(f'Logged in as {self.nick} and user id {self.user_id}')

    # message handler
    async def event_message(self, message):
        if message.echo:
            self._last_message_was_me = True
            return
        
        else:
            self._last_message_was_me = False

        await self.handle_commands(message)

    # routine definitions
    @routines.routine(minutes=5, wait_first=True)
    async def automated_songbot_helper(self):
        if not self._last_message_was_me:
            await self.send_message_to_chat(f'SongBot quickstart: !list for a link to a full menu of songs, !request <song> to request a specific song.')

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)-15s [%(levelname)s] %(funcName)s: %(message)s")
    bot = JulieBot()
    bot.run()