import discord
from discord.ext import commands
from cogs.utils.dataIO import fileIO
from cogs.utils.chat_formatting import *

import datetime

class BotInfo:
    def __init__(self,bot):
        self.bot = bot

    @property
    def join_message(self):
        ret = bold("Hey there!") + "\n"
        ret += "I'm Squid and I just got asked to join this server.\n"
        ret += "If you don't want me here feel free to kick me.\n"
        ret += "Otherwise, my current prefixes are", self.bot.command_prefix
        ret += " and you can see all of my commands by running "
        ret += inline(str(self.bot.command_prefix)+"help")
        return ret

    async def serverjoin(server):
        channel = server.default_channel
        print('Joined {} at {}'.format(server.name,datetime.datetime.now()))
        await self.bot.send_message(channel,self.join_message)

def setup(bot):
    n = BotInfo(bot)
    bot.add_listener(n.serverjoin, "on_server_join")