import discord
from discord.ext import commands
from .utils import checks
from .utils.chat_formatting import *
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
import os
import datetime

class MentionTracker:
    def __init__(self,bot):
        self.bot = bot
        self.mail = fileIO("data/mentiontracker/mail.json","load")
        self.settings = fileIO("data/mentiontracker/settings.json","load")

    @commands.group(pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def mentionset(self,ctx):
        """Manage mentiontracker settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            msg = "```"
            for k, v in self.settings.items():
                msg += str(k) + ": " + str(v) + "\n"
            msg += "```"
            await self.bot.say(msg)

    @mentionset.command(name="limit",pass_context=True)
    async def _mentionset_limit(self,ctx,num : int):
        """Number of minutes to wait in between saving mentions."""
        if num < 0:
            send_cmd_help(ctx)
            return
        self.settings["MENTION_TIME_LIMIT"] = num
        fileIO("data/mentiontracker/settings.json","save",self.settings)
        self.bot.say("Settings saved.")

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
            await self.bot.reply("thanks for registering.")
        else:
            await self.bot.reply("you're already registered.")

    @mention.command(pass_context=True,name="read")
    async def _mention_read(self,ctx):
        """Read all mentions since you've been away."""
        user = ctx.message.author
        if user.id not in self.mail:
            await self.bot.reply("you're not registered!")
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
        mail["message"] = self._clean_message(message)
        mail["server"] = message.server.name
        mail["channel"] = message.channel.name
        mail["time"] = str(message.timestamp)
        self.mail[add_id].append(mail)
        fileIO("data/mentiontracker/mail.json","save",self.mail)

    def _clean_message(self,message):
        ret = message.content
        for user in message.mentions:
            ret = ret.replace(user.mention,"@"+user.name)
        return ret

    def _last_time(self,mention):
        mail = self.mail[mention.id]
        if len(mail) > 0:
            last_mention = mail[-1]
            return datetime.datetime.strptime(last_mention["time"],"%Y-%m-%d %H:%M:%S.%f")
        else:
            return datetime.datetime.min

    async def tracker(self,message):
        if message.author == self.bot.user:
            return
        mentions = message.mentions
        for mention in mentions:
            if mention != message.author and mention.id in self.mail and 'on' not in mention.status:
                limit = self.settings.get("MENTION_TIME_LIMIT",0)
                delta = datetime.timedelta(minutes=limit)
                if self._last_time(mention) + delta < datetime.datetime.utcnow():
                    self._add_mail(mention.id,message)

def check_folder():
    if not os.path.exists("data/mentiontracker"):
        print("Creating data/mentiontracker folder...")
        os.makedirs("data/mentiontracker")

def check_file():
    mail = {}
    settings = {"MENTION_TIME_LIMIT":5}

    f = "data/mentiontracker/mail.json"
    if not fileIO(f, "check"):
        print("Creating default mentiontracker's mail.json...")
        fileIO(f, "save", mail)

    f = "data/mentiontracker/settings.json"
    if not fileIO(f, "check"):
        print("Creating default mentiontracker's settings.json...")
        fileIO(f, "save", settings)

def setup(bot):
    check_folder()
    check_file()
    n = MentionTracker(bot)
    bot.add_listener(n.tracker, "on_message")
    bot.add_cog(n)