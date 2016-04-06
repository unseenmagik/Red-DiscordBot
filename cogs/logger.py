import discord
from discord.ext import commands
from cogs.utils.dataIO import fileIO
from cogs.utils import checks
import os


class ChannelLogger(object):
    """docstring for ChannelLogger"""

    def __init__(self, bot):
        super(ChannelLogger, self).__init__()
        self.bot = bot

        self.channels = fileIO("data/channellogger/channels.json", "load")

    @commands.command(pass_context=True)
    async def logger(self, ctx):
        """Toggles logging for a channel"""
        pass

    async def log():
        pass

    async def on_message(self, message):
        if message.channel.id in self.channels:
            discord.utils.soemthing(self.log(message))


def check_folders():
    if not os.path.exists("data/channellogger"):
        os.mkdir("data/channellogger")


def check_files():
    if not os.path.exists("data/channellogger/channels.json"):
        fileIO("data/channellogger/channels.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = ChannelLogger(bot)
    bot.add_cog(n)
    bot.add_extension(n.message_logger, "on_message")
