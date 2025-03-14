import os
import logging
import asyncio
import sqlite3
import asqlite

import twitchio
from twitchio.ext import commands
from twitchio import eventsub

logger = logging.getLogger(__name__)

class JulieBot(commands.Bot):
    def __init__(self, *, token_database: asqlite.Pool) -> None:
        self.token_database = token_database
        super().__init__(
            client_id=os.environ["CLIENT_ID"],
            client_secret=os.environ["CLIENT_SECRET"],
            bot_id=os.environ["BOT_ID"],
            owner_id=os.environ["OWNER_ID"],
            prefix="!",
        )

    async def setup_hook(self) -> None:
        await self.add_component(CustomCommandsComponent(self))

        subscription = eventsub.ChatMessageSubscription(broadcaster_user_id=os.environ["OWNER_ID"], user_id=os.environ["BOT_ID"])
        await self.subscribe_websocket(payload=subscription)

        subscription = eventsub.StreamOnlineSubscription(broadcaster_user_id=os.environ["OWNER_ID"])
        await self.subscribe_websocket(payload=subscription)

    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(token, refresh)

        query = """
        INSERT INTO tokens (user_id, token, refresh)
        VALUES (?, ? ,?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            token = excluded.token,
            refresh = excluded.refresh;
        """

        async with self.token_database.acquire() as connection:
            await connection.execute(query, (resp.user_id, token, refresh))

        logger.info("added token to db for user: %s", resp.user_id)
        return resp
    
    async def load_tokens(self, path: str | None = None) -> None:
        async with self.token_database.acquire() as connection:
            rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * FROM tokens""")

        for row in rows:
            await self.add_token(row["token"], row["refresh"])

    async def setup_database(self) -> None:
        query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
        async with self.token_database.acquire() as connection:
            await connection.execute(query)

    async def event_ready(self) -> None:
        logger.info("OK: logged in as %s", self.bot_id)


class CustomCommandsComponent(commands.Component):
    def __init__(self, bot: JulieBot):
        self.bot = bot

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        logger.info(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")

    @commands.command(aliases=["songs", "sl", "list"])
    @commands.cooldown(rate=1, per=60, key=commands.BucketType.channel)
    async def songlist(self, ctx: commands.Context) -> None:
        await ctx.reply(f"@{ctx.chatter.name}, here's the link: https://t.ly/ezltR")

    @commands.command()
    @commands.is_elevated()
    async def adbreak(self, ctx: commands.Context) -> None:
        await ctx.send("!!! we're going on ad break shortly - we run 3m ads to fully poof away the pre-roll ads, so please sit tight! don't worry, no requests or music will be happening during the ads julien130Lopheart !!!")

    @commands.command()
    @commands.is_broadcaster()
    async def raidmsg(self, ctx: commands.Context) -> None:
        await ctx.send(f"!!! we're raiding out - please copy the following message and give them all of the warm and fuzzy plink-plonks when you arrive !!!")
        await ctx.send("julien130Namalove plink plonks peeps have arrived! julien130Namalove")


def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)

    async def runner() -> None:
        async with asqlite.create_pool("tokens.db") as token_database, JulieBot(token_database=token_database) as bot:
            await bot.setup_database()
            await bot.start()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        logger.warning("--- shutting down due to keyboard interrupt ---")

if __name__ == "__main__":
    main()