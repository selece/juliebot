import logging
import os


from datetime import datetime, timedelta
from twitchio.ext import commands, routines
from db import DB

logger = logging.getLogger(__name__)
db = DB.instance()

class CheckInCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.checkins = []
        self.checkins_allowed = False

        if db.add_broadcast_to_db():
            self.checkins_allowed = True

    # message sender
    async def send_message_to_chat(self, message: str) -> None:
        for channel in self.bot.connected_channels:
            await channel.send(message)

    @commands.cooldown(rate=1, per=1, bucket=commands.Bucket.user)
    @commands.command(aliases=("c", "check", "ci"))
    async def checkin(self, ctx: commands.Context) -> None:
        if not self.checkins_allowed:
            return

        logging.info(f'checkin for user: {ctx.author.name} {ctx.author.id}')
        
        if ctx.author.id in self.checkins:
            logging.info(f'user already checked in this session: {ctx.author.name} {ctx.author.id}')
            return
        
        self.checkins.append(ctx.author.id)
        watch_streak = db.record_checkinuser(ctx.author.id)
        await self.send_message_to_chat(f'@{ctx.author.name} checked in! julien130Lopheart current watch streak: {watch_streak}')

        