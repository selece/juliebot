import logging
import os

from dataclasses import dataclass
from datetime import datetime, timedelta
from twitchio.ext import commands, routines
from db import DB

logger = logging.getLogger(__name__)
db = DB.instance()

MOOD_RESPONSES = {
    1: [
        "that's rough :( i hope it gets better for you soon!",
        ""
    ]
}

@dataclass
class MoodUser:
    id: int
    twitch_id: int
    mood: int
    last_checkin: int

class MoodCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self._mood_check_active = False
        self._mood_check_started_timestamp = datetime.now()
        self._mood_updates = {}
        self._mood_check_duration = timedelta(minutes=int(os.environ['MOOD_COG_CHECKIN_DURATION']))
        self._min_mood = int(os.environ['MOOD_COG_MIN_RATING'])
        self._max_mood = int(os.environ['MOOD_COG_MAX_RATING'])

        self.automated_mood_checkin.start()

    async def send_message_to_chat(self, message: str) -> None:
        for channel in self.bot.connected_channels:
            await channel.send(message)

    @commands.command()
    async def mood(self, ctx: commands.Context, mood: int) -> None:
        if not self._mood_check_active:
            await self.send_message_to_chat(f'sorry @{ctx.author.name}, there is no mood check currently open')
            return
        
        author = int(ctx.author.id)
        
        if author in self._mood_updates:
            return
        
        if mood > 5:
            mood = 5

        if mood < 1:
            mood = 1
        
        self._mood_updates[author] = mood

    @commands.command()
    async def moodcheck(self, ctx: commands.Context, duration: int | None):
        if not ctx.author.is_broadcaster or not ctx.author.is_mod:
            return
        
        if self._mood_check_active:
            remaining_duration = self._mood_check_duration-(datetime.now()-self._mood_check_started_timestamp)
            logging.info(f'mood check already active; not starting a new one ({remaining_duration} remaining in current window)')
            await self.send_message_to_chat(f'there is a mood check currently active - please let me know how you\'re feeling by using !mood <{self._min_mood} - {self._max_mood}> to record your mood <3')
            return

        if duration is not None:
            self._mood_check_duration = timedelta(minutes=int(duration))

        self._mood_check_active = True
        self._mood_check_started_timestamp = datetime.now()
        self._mood_updates = {}
        await self.send_message_to_chat(f'how are you all feeling today? let me know! use !mood <{self._min_mood} - {self._max_mood}> to record your mood and i will keep track of it for you!')

    @routines.routine(seconds=1)
    async def automated_mood_checkin(self) -> None:
        if not self._mood_check_active:
            return
        
        now_timestamp = datetime.now()
        if now_timestamp - self._mood_check_started_timestamp > self._mood_check_duration:
            self._mood_check_active = False

            for twitch_id, mood in self._mood_updates.items():
                logging.info(f'mood data: {twitch_id} {mood}')

                user = db.get_mooduser_from_db(twitch_id)
                if user is None:
                    db.add_mooduser_to_db(twitch_id)
                    user = db.get_mooduser_from_db(twitch_id)
                
                db.record_mooduser(twitch_id, mood)
                logging.info(f'last mood: {twitch_id} -> {db.get_last_mood(twitch_id)}')
                logging.info(f'average mood: {db.get_average_mood(twitch_id)}')

            self._mood_updates = {}

