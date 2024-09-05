import logging
import os
import requests

from dataclasses import dataclass
from datetime import datetime, timedelta
from twitchio.ext import commands, routines
from db import DB

logger = logging.getLogger(__name__)
db = DB.instance()

@dataclass
class Pun:
    id: int
    pun_id: int
    pun_text: str
    rating: int
    ban: int

class PunsCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self._pun_vote_active = False
        self._pun_vote_started_timestamp = datetime.now()
        self._pun_votes = {}
        self._pun_id = 0
        self._pun_min_rating = int(os.environ['PUNS_COG_MIN_RATING'])
        self._pun_max_rating = int(os.environ['PUNS_COG_MAX_RATING'])

        # default to 1-5 if the settings are wonky
        if self._pun_min_rating >= self._pun_max_rating:
            self._pun_min_rating = 1
            self._pun_max_rating = 5

        self.PUN_VOTE_WINDOW = timedelta(seconds=int(os.environ['PUNS_COG_PUN_VOTE_WINDOW']))
        self.MAX_PUN_API_RETRIES = int(os.environ['PUNS_COG_PUN_API_RETRIES'])

        self.automated_pun_vote.start()

    async def send_message_to_chat(self, message: str) -> None:
        for channel in self.bot.connected_channels:
            await channel.send(message)

    # random pun
    @commands.cooldown(rate=1, per=int(os.environ['PUNS_COG_PUN_COOLDOWN_PER_USER']), bucket=commands.Bucket.channel)
    @commands.command()
    async def pun(self, ctx: commands.Context) -> None:
        pun, is_new = self.get_pun_from_api()

        if pun is None:
            await self.send_message_to_chat(f'sorry @{ctx.author.name}! the pun api does not seem to be working right now... BibleThump')
            return

        self._pun_vote_active = True
        self._pun_vote_started_timestamp = datetime.now()

        await self.send_message_to_chat(f'{pun.pun_text}')
        await self.send_message_to_chat(f'please rate my pun using !ratepun <{self._pun_min_rating}-{self._pun_max_rating}>, {self._pun_min_rating} (terrible) to {self._pun_max_rating} (amazing)! voting will be open for the next 30 seconds... <3')

        if not is_new:
            await self.send_message_to_chat(f'the last time this pun got picked, it was rated {pun.rating}')

    # rate pun
    @commands.cooldown(rate=1, per=int(os.environ['PUNS_COG_PUN_COOLDOWN_PER_USER']), bucket=commands.Bucket.user)
    @commands.command(aliases=("rp"))
    async def ratepun(self, ctx: commands.Context, rating: int) -> None:
        if ctx.author.name in self._pun_votes:
            return
        
        if not self._pun_vote_active:
            return
        
        if rating > self._pun_max_rating:
            rating = self._pun_max_rating

        if rating < self._pun_min_rating:
            rating = self._pun_min_rating
        
        self._pun_votes[ctx.author.name] = rating

    # ban pun
    @commands.command()
    async def banpun(self, ctx: commands.Context) -> None:
        if not ctx.author.is_broadcaster or ctx.author.is_mod:
            return
        
        if not self._pun_vote_active:
            return
        
        db.ban_pun(self._pun_id)

    @routines.routine(seconds=1)
    async def automated_pun_vote(self) -> None:
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

    # pun api
    def get_pun_from_api(self) -> tuple[Pun|None, bool]:
        retry_count = 0

        while retry_count < self.MAX_PUN_API_RETRIES:
            req: requests.Response = requests.get('https://punapi.rest/api/pun', headers={'user-agent': 'juliebot @ https://github.com/selece/juliebot'})

            if req.status_code != 200:
                return None, False
        
            json_response = req.json()

            pun_id: int = int(json_response['id'])
            pun_text: str = json_response['pun']
            pun_is_banned: bool = False
            pun_record: tuple = None
            pun_is_new = False

            if db.check_if_pun_exists(pun_id):
                pun_record = db.get_pun_from_db(pun_id)
                pun_is_banned = pun_record[3] == 1

            else:
                db.add_pun_to_db(pun_id)
                pun_record = db.get_pun_from_db(pun_id)
                pun_is_new = True

            if not pun_is_banned:
                self._pun_id = pun_id
                return Pun(id=pun_record[0], pun_id=pun_record[1], pun_text=pun_text, rating=pun_record[2], ban=pun_record[3]), pun_is_new
            else:
                retry_count += 1

        return None, False