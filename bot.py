import datetime
import json
import os
import logging
import requests

import asyncio
import sqlite3
import asqlite

from dotenv import load_dotenv

import twitchio
from twitchio.authentication import UserTokenPayload
from twitchio.ext import commands
from twitchio import eventsub

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

LOGGER: logging.Logger = logging.getLogger("JulieBot")
class JulieBot(commands.AutoBot):
    def __init__(self, *, database: asqlite.Pool, subs: list[eventsub.SubscriptionPayload]) -> None:
        self.database = database
        super().__init__(
            client_id=os.environ["CLIENT_ID"],
            client_secret=os.environ["CLIENT_SECRET"],
            bot_id=os.environ["BOT_ID"],
            owner_id=os.environ["OWNER_ID"],
            prefix="!",
            subscriptions=subs,
            force_subscribe=True,
        )

    async def setup_hook(self) -> None:
        await self.add_component(CustomCommandsComponent())

    async def event_oauth_authorized(self, payload: UserTokenPayload) -> None:
        await self.add_token(payload.access_token, payload.refresh_token)

        if not payload.user_id:
            return
        
        if payload.user_id == self.bot_id:
            return
        
        subs: list[eventsub.SubscriptionPayload] = [
            eventsub.ChatMessageSubscription(broadcaster_user_id=payload.user_id, user_id=self.bot_id),
            eventsub.ChannelSubscribeSubscription(broadcaster_user_id=payload.user_id),
        ]

        resp: twitchio.MultiSubscribePayload = await self.multi_subscribe(subs)
        if resp.errors:
            LOGGER.warning("Failed to subscribe to %r using user %r", resp.errors, payload.user_id)

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

        async with self.database.acquire() as connection:
            await connection.execute(query, (resp.user_id, token, refresh))

        LOGGER.info("Added token to db for user: %s", resp.user_id)
        return resp

    async def event_ready(self) -> None:
        LOGGER.info("OK: logged in as %s", self.bot_id)

class CustomCommandsComponent(commands.Component):
    def __init__(self):
        pass

    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        LOGGER.info(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")

    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        LOGGER.info(f"subscribe: {payload.user} @ {payload.tier}")
        
    @commands.command(aliases=["songs", "sl", "list"])
    @commands.cooldown(rate=1, per=60, key=commands.BucketType.channel)
    async def songlist(self, ctx: commands.Context) -> None:
        await ctx.reply(f"@{ctx.chatter.name}, here's the link: https://t.ly/ezltR")

    @commands.command()
    @commands.is_elevated()
    async def adbreak(self, ctx: commands.Context) -> None:
        await ctx.send("!!! we're going on ad break shortly - we run 3m ads to fully poof away the pre-roll ads, so please sit tight! don't worry, no requests or music will be happening during the ads julien130Lopheart !!!")

    @commands.command()
    @commands.is_elevated()
    async def raidmsg(self, ctx: commands.Context) -> None:
        await ctx.send(f"!!! we're raiding out - please copy the following message and give them all of the warm and fuzzy plink-plonks when you arrive !!!")
        await ctx.send("julien130Namalove plink plonks peeps have arrived! julien130Namalove")

    @commands.command(aliases=["what"])
    @commands.cooldown(rate=1, per=datetime.timedelta(seconds=5), key=commands.BucketType.channel)
    async def whatsong(self, ctx: commands.Context) -> None:
        req = requests.get("http://localhost:8080/requests/status.json", auth=("", "vlc"))

        if req.status_code != 200:
            await ctx.reply(f"oops! some sort of weird error happened and i'm not sure what to do with it. sorry!")
            return
        
        json_resp = json.loads(req.text)
        if json_resp["state"] != "playing":
            await ctx.reply(f"hmm, it doesn't look like we're currently playing a song...")
            return
        
        album = json_resp["information"]["category"]["meta"]["album"]
        artist = json_resp["information"]["category"]["meta"]["artist"]
        title = json_resp["information"]["category"]["meta"]["title"]
        await ctx.reply(f"{title} - {album} ({artist})")

    @commands.command(aliases=["next"])
    @commands.cooldown(rate=1, per=datetime.timedelta(seconds=30), key=commands.BucketType.channel)
    async def nextsong(self, ctx: commands.Context) -> None:
        req = requests.get("http://localhost:8080/requests/status.json", auth=("", "vlc"))

        if req.status_code != 200:
            await ctx.reply(f"oops! some sort of weird error happened and i'm not sure what to do with it. sorry!") 
            return
        
        json_resp = json.loads(req.text)
        if json_resp["state"] != "playing":
            await ctx.reply(f"hmm, it doesn't look like we're currently playing a song...")
            return

        req = requests.get("http://localhost:8080/requests/status.xml?command=pl_next", auth=("", "vlc"))

        if req.status_code != 200:
            await ctx.reply(f"oops! some sort of weird error happened and i'm not sure what to do with it. sorry!")
            return
        
        await ctx.reply(f"okiedokie, skipping to next song on the breaktime playlist! (we can't skip a song for another 30 seconds)")

    @commands.command()
    @commands.cooldown(rate=1, per=datetime.timedelta(seconds=15), key=commands.BucketType.user)
    async def help(self, ctx: commands.Context) -> None:
        await ctx.reply(f"available commands [+aliases]: !songlist [!list !songs !sl]; !whatsong [!what]; !nextsong [!next]")

async def setup_database(db: asqlite.Pool) -> tuple[list[tuple[str, str]], list[eventsub.SubscriptionPayload]]:
    query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
    async with db.acquire() as connection:
        await connection.execute(query)
        
        rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")
        tokens: list[tuple[str, str]] = []
        subs: list[eventsub.SubscriptionPayload] = []

        for row in rows:
            tokens.append((row["token"], row["refresh"]))

            if row["user_id"] == os.environ["BOT_ID"]:
                continue

            subs.extend([eventsub.ChatMessageSubscription(broadcaster_user_id=row["user_id"], user_id=os.environ["BOT_ID"])])

    return tokens, subs

def main() -> None:
    load_dotenv()
    twitchio.utils.setup_logging(level=logging.INFO)

    async def runner() -> None:
        async with asqlite.create_pool("tokens.db") as token_database:
            tokens, subs = await setup_database(token_database)

            async with JulieBot(database=token_database, subs=subs) as bot:
                for pair in tokens:
                    await bot.add_token(*pair)

                await bot.start(load_tokens=False)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("--- shutting down due to keyboard interrupt ---")

if __name__ == "__main__":
    main()