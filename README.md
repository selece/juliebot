# intro
This is the public repo for JulieBot - a twitch.tv streamchat bot with some basic commands.

Personal project; feel free to copy or extend.

# .env setup
```
# basic setup
# twitch oauth token, formatted like oauth:abcdef012345
TOKEN=

# bot nickname to use for chat identity
BOT_NICK=JulieBot

# prefix for bot commands, i.e. ! results in commands like !help
BOT_PREFIX=!

# channel to connect to on startup; only one channel supported for now
CHANNEL=julie_never_streams


# chat activity monitor, if messages are not sent within this time in minutes triggers the inactivity callback
CHAT_INACTIVITY_TIMER=1


# puns cog setup
# vote window in seconds for rating puns; opens immediately after a pun is posted
PUNS_COG_PUN_VOTE_WINDOW=30

# retries to the pun api allowed in case of failure
PUNS_COG_PUN_API_RETRIES=10

# cooldown per user on pun command, in seconds
PUNS_COG_PUN_COOLDOWN_PER_USER=30

# integer minimum for bottom of rating scale
PUNS_COG_MIN_RATING=1

# integer maximum for top of rating scale
PUNS_COG_MAX_RATING=5


# songs cog setup
# url for the !songlist command to echo into chat for requesting a song
SONGS_COG_URL=https://www.streamersonglist.com/t/julie_never_streams/songs

# cooldown in seconds for !songlist command channel-wide
SONGS_COG_LIST_COMMAND_FREQUENCY=10

# delay in minutes between automatic help for songbot message frequency
SONGS_COG_HELPER_MESSAGE_FREQUENCY=5


# mood cog setup
# how long in minutes the check will be open for once !moodcheck is used
MOOD_COG_CHECKIN_DURATION=1

# integer minimum for mood rating
MOOD_COG_MIN_RATING=1

# integer maximum for mood rating
MOOD_COG_MAX_RATING=5
```