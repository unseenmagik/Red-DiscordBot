import discord
from discord.ext import commands
from .utils import checks
from .utils.chat_formatting import *
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
import os

class MentionTracker:
    def __init__(self,bot):
        self.bot = bot
        self.mail = fileIO("data/mentiontracker/mail.json","load")

    @commands.group(pass_context=True)
    async def mention(self,ctx):
        """Saves your mentions when you're not online."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @mention.command(pass_context=True,name="register")
    async def _mention_register(self,ctx):
        """Register yourself for mention tracking"""
        user = ctx.message.author
        if user.id not in self.mail:
            self.mail[user.id] = []
            fileIO("data/mentiontracker/mail.json","save",self.mail)
        else:
            await self.bot.reply("You're already registered.")

    @mention.command(pass_context=True,name="read")
    async def _mention_read(self,ctx):
        """Read all mentions since you've been away."""
        user = ctx.message.author
        if user.id not in self.mail:
            await self.bot.reply("You're not registered!")
            temp_context = ctx
            temp_context.invoked_subcommand = self._mention_register
            await send_cmd_help(temp_context)
            return
        if len(self.mail[user.id]) == 0:
            await self.bot.say("You have no mentions.")
            return
        for mail in self.mail[user.id]:
            await self.bot.whisper(self._fmt_mail(mail))
        self.mail[user.id] = []
        fileIO("data/mentiontracker/mail.json","save",self.mail)

    def _fmt_mail(self,mail):
        author = mail.get("author","no_author")
        message = mail.get("message","no_message")
        server = mail.get("server","no_server")
        channel = mail.get("channel","no_channel")
        time = mail.get("time","no_time")
        ret = "A message from {} at {} UTC:\n".format(author,time)
        ret += "\tServer: {}\n".format(server)
        ret += "\tChannel: {}\n".format(channel)
        ret += "\tMessage:\n{}".format(message)
        return box(ret)

    def _add_mail(self,add_id,message):
        mail = {}
        mail["author"] = message.author.name
        mail["message"] = message.content
        mail["server"] = message.server.name
        mail["channel"] = message.channel.name
        mail["time"] = str(message.timestamp)
        self.mail[add_id].append(mail)
        fileIO("data/mentiontracker/mail.json","save",self.mail)

    async def tracker(self,message):
        if message.author == self.bot.user:
            return
        mentions = message.mentions
        for mention in mentions:
            if mention != message.author and mention.id in self.mail and message.author.status != 'online':
                self._add_mail(mention.id,message)

def check_folder():
    if not os.path.exists("data/mentiontracker"):
        print("Creating data/mentiontracker folder...")
        os.makedirs("data/mentiontracker")

def check_file():
    mail = {}

    f = "data/mentiontracker/mail.json"
    if not fileIO(f, "check"):
        print("Creating default mentiontracker's mail.json...")
        fileIO(f, "save", mail)

def setup(bot):
    check_folder()
    check_file()
    n = MentionTracker(bot)
    bot.add_listener(n.tracker, "on_message")
    bot.add_cog(n)