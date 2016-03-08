import discord
from discord.ext import commands
import feedparser
import os
import time
import aiohttp
import asyncio
import datetime

import cogs.utils.checks as checks
from cogs.utils.dataIO import fileIO
from cogs.utils.chat_formatting import *
from __main__ import send_cmd_help
from i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('RSS')

class Settings(object):
    pass

class Feeds(object):
    def __init__(self):
        self.check_folders()
        # {server:{name:[chanid,url,last_scraped]}}
        self.feeds = fileIO("data/RSS/feeds.json","load")

    def save_feeds(self):
        fileIO("data/RSS/feeds.json","save",self.feeds)

    def check_folders(self):
        if not os.path.exists("data/RSS"):
            print("Creating data/RSS folder...")
            os.makedirs("data/RSS")
        self.check_files()

    def check_files(self):
        f = "data/RSS/feeds.json"
        if not fileIO(f, "check"):
            print("Creating empty feeds.json...")
            fileIO(f, "save", {})

    def update_time(self,server,name,time):
        if server in self.feeds:
            if name in self.feeds.get(server):
                prev = self.feeds[server].get(name)
                prev[2] = time
                self.feeds[server][name] = prev
        self.save_feeds()

    def add_feed(self, ctx, name, url):
        server = ctx.message.server.id
        channel = ctx.message.channel.id
        if server not in self.feeds:
            self.feeds[server] = {}
        self.feeds[server][name] = [channel,url,()]
        self.save_feeds()

    async def delete_feed(self,ctx,name):
        server = ctx.message.server.id
        if server not in self.feeds:
            await self.bot.say('That feed doesn\'t exist on this server!')
            return
        if name not in self.feeds[server]:
            await self.bot.say('That feed doesn\'t exist on this server!')
            return
        del self.feeds[server][name]
        self.save_feeds()

    def get_feed_names(self,server):
        if server not in self.feeds:
            return {}
        ret = (k for k in self.feeds[server].copy().keys())
        return ret

    def get_copy(self):
        return self.feeds.copy()

class RSS(object):
    def __init__(self, bot):
        self.bot = bot

        self.settings = Settings()
        self.feeds = Feeds()

        self.register_events()

    def register_events(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.read_feeds())

    def get_channel_object(self, channel_id):
        return self.bot.get_channel(channel_id)

    async def _get_feed(self, url):
        text = None
        try:
            with aiohttp.ClientSession() as session:
                with aiohttp.Timeout(3):
                    async with session.get(url) as r:
                        text = await r.text()
        except:
            pass
        return text

    async def valid_url(self,url):
        text = await self._get_feed(url)
        try:
            rss = feedparser.parse(text)
        except:
            return False
        else:
            return True

    @commands.group(pass_context=True)
    @internationalizeDocstring
    async def rss(self,ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @rss.command(pass_context=True,name="add")
    @internationalizeDocstring
    async def _rss_add(self, ctx, name : str, url : str):
        valid_url = await self.valid_url(url)
        if valid_url:
            self.feeds.add_feed(ctx,name,url)
            await self.bot.say('Feed "{}" added.'.format(name))
        else:
            await self.bot.say('Invalid or unavailable URL.')

    @rss.command(pass_context=True,name="remove")
    @internationalizeDocstring
    async def _rss_remove(self, ctx, name : str):
        serverid = ctx.message.server.id
        if name in self.feeds.get_feed_names(serverid):
            await self.feeds.delete_feed(ctx,name)
            await self.bot.say('Feed deleted.')
        else:
            await self.bot.say('Feed "{}" not found.'.format(name))

    async def read_feeds(self):
        await self.bot.wait_until_ready()
        while 'RSS' in self.bot.cogs:
            feeds = self.feeds.get_copy()
            for server in feeds:
                for name, (chan_id,url,last_time) in feeds[server].items():
                    text = await self._get_feed(url)
                    try:
                        rss = feedparser.parse(text)
                    except:
                        continue
                    else:
                        curr_time = rss.entries[0].published_parsed[:5]
                        curr_datetime = datetime.datetime(*curr_time)
                        if len(last_time) == 0 or curr_datetime > datetime.datetime(*last_time):
                            channel = self.get_channel_object(chan_id)
                            message = ""
                            message += bold("Feed {}:\n".format(name))
                            message += rss.entries[0].title + "\n"
                            await self.bot.send_message(channel,message)
                            self.feeds.update_time(server,name,curr_time)
            await asyncio.sleep(60)

Class = RSS