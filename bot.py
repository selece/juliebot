import datetime
import json
import os
import logging
import requests

import asyncio
import asqlite

from dotenv import load_dotenv

import twitchio
from twitchio.ext import commands
from twitchio import eventsub

from commands.command_adbreak import CommandAdbreak
from commands.command_songlist import CommandSongList
from commands.command_raidmsg import CommandRaidMsg
from commands.command_vlc import CommandVlc

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
    
    async def setup_hook(self) -> None:
        await self.add_component(CommandAdbreak())
        await self.add_component(CommandSongList())
        await self.add_component(CommandRaidMsg())
        await self.add_component(CommandVlc())

    async def event_ready(self) -> None:
        LOGGER.info("OK: logged in as %s", self.bot_id)

    async def event_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        LOGGER.info(f"subscribe: {payload.user} @ {payload.tier}")

    async def event_ad_break(self, payload: twitchio.ChannelAdBreakBegin) -> None:
        await payload.respond(f"Ad break is starting now! Nothing interesting will happen until we're back, *pinky promise*. <3")

    async def event_custom_redemption_add(self, payload: twitchio.ChannelPointsRedemptionAdd) -> None:
        # await payload.respond(f"okies! {payload.reward.id} for {payload.reward.cost} from {payload.user.id}")
        LOGGER.info(f"okies! {payload.reward.id} for {payload.reward.cost} from {payload.user.id}")

    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        await payload.respond(f"Thanks for the follow! Follows are 100% anonymous - please make yourself comfy and cozy!")

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

            subs.extend([
                eventsub.ChatMessageSubscription(broadcaster_user_id=row["user_id"], user_id=os.environ["BOT_ID"]),
                eventsub.ChannelSubscribeSubscription(broadcaster_user_id=row["user_id"]),
                eventsub.AdBreakBeginSubscription(broadcaster_user_id=row["user_id"]),
                eventsub.ChannelFollowSubscription(broadcaster_user_id=row["user_id"], moderator_user_id=row["user_id"]),
            ])

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