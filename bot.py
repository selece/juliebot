import os
import requests
import logging

from datetime import datetime, timedelta

from db import DB
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

        # routines 
        for _r in [ self.automated_songbot_helper, self.automated_chat_monitor, self.automated_pun_vote ]:
            _r.start()

        # vars
        self._last_message_was_me = False
        self._last_active_chat_timestamp = datetime.now()

        self._pun_vote_active = False
        self._pun_vote_started_timestamp = datetime.now()
        self._pun_votes = {}
        self._pun_id = 0

        # config
        self.CHAT_INACTIVITY_TIMER = timedelta(minutes=1)
        self.PUN_VOTE_WINDOW = timedelta(seconds=30)

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
            self._last_message_was_me = True
            return
        
        else:
            self._last_message_was_me = False
            self._last_active_chat_timestamp = datetime.now()

        await self.handle_commands(message)

    # songlist
    @commands.cooldown(rate=1, per=10, bucket=commands.Bucket.channel)
    @commands.command(aliases=("list", "sl", "slist"))
    async def songlist(self, ctx: commands.Context):
        await self.send_message_to_chat(f'hey @{ctx.author.name}, here\'s the song list link! https://www.streamersonglist.com/t/julie_never_streams/songs')

    # random pun
    @commands.cooldown(rate=1, per=30, bucket=commands.Bucket.channel)
    @commands.command()
    async def pun(self, ctx: commands.Context):
        req: requests.Response = requests.get('https://punapi.rest/api/pun')

        if req.status_code != 200:
            await self.send_message_to_chat(f'sorry @{ctx.author.name}! the pun api does\'nt seem to be working right now... BibleThump')
            return
        
        json_response = req.json()
        pun_id: int = int(json_response['id'])
        pun_text: str = json_response['pun']

        logger.info(f'fetched pun: {pun_id} - {pun_text}')

        pun_record: tuple = None
        if db.check_if_pun_exists(pun_id):
            pun_record = db.get_pun_from_db(pun_id)

        else:
            db.add_pun_to_db(pun_id)

        self._pun_vote_active = True
        self._pun_vote_started_timestamp = datetime.now()
        self._pun_id = pun_id
        await self.send_message_to_chat(f'i have a pun for you @{ctx.author.name}: {pun_text}')
        await self.send_message_to_chat(f'please rate my pun using !ratepun <1-10>, 1 (terrible) to 10 (amazing)! voting will be open for the next 30 seconds... <3')

        if pun_record is not None:
            await self.send_message_to_chat(f'the last time this pun got picked, it was rated {pun_record[2]}')

    # rate pun
    @commands.cooldown(rate=1, per=30, bucket=commands.Bucket.user)
    @commands.command(aliases=("rp"))
    async def ratepun(self, ctx: commands.Context, rating: int):
        if ctx.author.name in self._pun_votes:
            return
        
        if not isinstance(rating, int):
            return
        
        if not self._pun_vote_active:
            return
        
        if rating > 10:
            rating = 10

        if rating < 1:
            rating = 1
        
        self._pun_votes[ctx.author.name] = rating

    # ban pun
    @commands.command()
    async def banpun(self, ctx: commands.Context):
        if not ctx.author.is_broadcaster or ctx.author.is_mod:
            return
        
        pass

    # routine definitions
    @routines.routine(minutes=5, wait_first=True)
    async def automated_songbot_helper(self):
        if not self._last_message_was_me:
            await self.send_message_to_chat(f'SongBot quickstart: !songlist for a link to a full menu of songs <3')

        else:
            logger.info(f'skipping automated songbot helper; last message was sent by me: {self._last_message_was_me}')

    @routines.routine(minutes=2, wait_first=True)
    async def automated_chat_monitor(self):
        now_timestamp = datetime.now()
        if now_timestamp - self._last_active_chat_timestamp > self.CHAT_INACTIVITY_TIMER:
            pass

    @routines.routine(seconds=1)
    async def automated_pun_vote(self):
        now_timestamp = datetime.now()
        if self._pun_vote_active and now_timestamp - self._pun_vote_started_timestamp > self.PUN_VOTE_WINDOW:
            self._pun_vote_active = False

            average_rating = 0.0
            total_votes = 0

            if len(self._pun_votes) > 0:
                for rating in self._pun_votes.values():
                    average_rating += rating
                    total_votes += 1

                average_rating = average_rating / total_votes
                await self.send_message_to_chat(f'closing pun voting! -- this pun will be rated {average_rating}')
            else:
                await self.send_message_to_chat(f'nobody liked that one... :( -- this pun will be rated {average_rating}')

            
            db.update_pun_rating(self._pun_id, average_rating)

            self._pun_votes = {}
            self._pun_id = 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)-15s [%(levelname)s] %(funcName)s: %(message)s")
    bot = JulieBot()
    bot.run()