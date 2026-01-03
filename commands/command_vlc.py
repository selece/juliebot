import datetime
import json
import logging
import os
import requests

from twitchio.ext import commands

LOGGER: logging.Logger = logging.getLogger("command_vlc")

ERROR_STR = "~err~"
NOTPLAYING_STR = "`~notplaying~"
REQ_TIMEOUT = 1.0

class CommandVlc(commands.Component):
    def __init__(self) -> None:
        self.vlc_address = os.environ.get("COMMAND_VLC_ADDRESS", "")
        self.vlc_auth = (os.environ.get("COMMAND_VLC_LOGIN", ""), os.environ.get("COMMAND_VLC_PASS", ""))

        if not self.vlc_address:
            LOGGER.error("no valid vlc address provided in env vars")
            self.vlc_available = False

        else:
            if not self.get_status():
                LOGGER.error(f"no valid vlc instance at provided address {self.vlc_address} - check env config")
                self.vlc_available = False
            else:
                LOGGER.info(f"successfully connected to vlc instance")
                self.vlc_available = True

    def get_status(self) -> bool:
        try:
            req = requests.get(self.get_status_url(), auth=self.vlc_auth, timeout=REQ_TIMEOUT)
        except requests.Timeout:
            return False

        if req.status_code != 200:
            return False
        else:
            return True

    def get_currently_playing(self) -> tuple[str, str, str]:
        if not self.vlc_available:
            return (ERROR_STR, ERROR_STR, ERROR_STR)

        try:
            req = requests.get(self.get_status_url(), auth=self.vlc_auth, timeout=REQ_TIMEOUT)
        except requests.Timeout:
            return (ERROR_STR, ERROR_STR, ERROR_STR)
        
        if req.status_code != 200:
            LOGGER.error(f"failed to retrieve status from VLC instance with code {req.status_code}")
            return (ERROR_STR, ERROR_STR, ERROR_STR)
        
        json_resp = json.loads(req.text)
        if json_resp["state"] != "playing":
            return (NOTPLAYING_STR, NOTPLAYING_STR, NOTPLAYING_STR)
        
        album = json_resp["information"]["category"]["meta"]["album"]
        artist = json_resp["information"]["category"]["meta"]["artist"]
        title = json_resp["information"]["category"]["meta"]["title"]

        return (album, artist, title)
    
    def get_status_url(self) -> str:
        return self.vlc_address + "/requests/status.json"
    
    def get_next_url(self) -> str:
        return self.vlc_address + "/requests/status.xml?command=pl_next"
    
    @commands.command(aliases=["what", "bgsong"])
    @commands.cooldown(rate=1, per=datetime.timedelta(seconds=30), key=commands.BucketType.channel)
    async def whatsong(self, ctx: commands.Context) -> None:
        if not self.vlc_available:
            return
        
        album, artist, title = self.get_currently_playing()

        if album == ERROR_STR:
            return
        elif album == NOTPLAYING_STR:
            await ctx.reply(f"@{ctx.chatter} it looks like we aren't playing anything in the background right now!")
            return
        
        await ctx.reply(f"@{ctx.chatter} - it's f{title} by f{artist} from f{album}")

    @commands.command(aliases=["skip", "next"])
    @commands.cooldown(rate=1, per=datetime.timedelta(seconds=30), key=commands.BucketType.channel)
    async def nextsong(self, ctx: commands.Context) -> None:
        if not self.vlc_available:
            return

        album, _, _ = self.get_currently_playing()

        if album == ERROR_STR:
            return
        elif album == NOTPLAYING_STR:
            await ctx.reply(f"@{ctx.chatter} it looks like we aren't playing anything in the background right now!")
            return
        
        try:
            req = requests.get(self.get_next_url(), auth=self.vlc_auth, timeout=REQ_TIMEOUT)
        except requests.Timeout:
            LOGGER.error(f"couldn't contact vlc instance")
            return

        if req.status_code != 200:
            LOGGER.error(f"failed to skip to next item on playlist with error {req.status_code}")
        else:
            await ctx.reply("okay! skipping to the next song on the playlist")
