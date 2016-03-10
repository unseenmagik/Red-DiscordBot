import discord
from discord.ext import commands
from discord import utils
from cogs.utils.dataIO import fileIO
from cogs.utils.chat_formatting import *
from __main__ import settings

import datetime

class BotInfo:
    def __init__(self,bot):
        self.bot = bot

    @property
    def prefixes(self):
        '''ret = "["
        middle = "|".join(self.bot.command_prefix)
        return ret+middle+"]"'''
        return self.bot.command_prefix[0]
    

    @property
    def join_message(self):
        ret = bold("Hey there!") + "\n"
        ret += "I'm Squid and I just got asked to join this server.\n"
        ret += "If you don't want me here feel free to kick me.\n"
        ret += "Otherwise, my current prefixes are " + self.prefixes
        ret += " and you can see all of my commands by running "
        ret += inline(self.prefixes+"help")
        ret += "\n\n"
        ret += italics("If you want a custom plugin made: ")
        ret += inline("~contact [desc]")
        ret += " and it will be sent to my owner.\n"
        ret += "I can also do " + bold('Twitch Emotes')+ "!\n"
        ret += "See "+inline(self.prefixes+"help Emotes")
        return ret

    @commands.command()
    async def servers(self):
        '''General global server information'''
        servers = sorted([server.name for server in self.bot.servers])
        ret = "I am currently in "
        ret += bold(len(servers))
        ret += " servers with "
        ret += bold(len([m for m in self.bot.get_all_members()]))
        ret += " members.\n"
        await self.bot.say(ret)

    @commands.command(pass_context=True)
    async def contact(self,ctx,*, message : str):
        """Send a message to my owner"""
        author = ctx.message.author.name
        server = ctx.message.server.name
        owner = utils.find(lambda mem: str(mem.id) == settings.owner,
                                        self.bot.get_all_members())
        message = "A message from {} on {}:\n\t{}".format(author,server,message)
        if owner is not None:
            await self.bot.send_message(owner,message)
        else:
            await self.bot.say("Sorry, my owner is offline, try again later?")

    async def serverjoin(self,server):
        channel = server.default_channel
        print('Joined {} at {}'.format(server.name,datetime.datetime.now()))
        try:
            await self.bot.send_message(channel,self.join_message)
        except discord.errors.Forbidden:
            pass

def setup(bot):
    n = BotInfo(bot)
    bot.add_listener(n.serverjoin, "on_server_join")
    bot.add_cog(n)