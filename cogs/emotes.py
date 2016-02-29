import discord
from discord.ext import commands
import aiohttp
import asyncio
from .utils import checks
from .utils.dataIO import fileIO
import os
from __main__ import send_cmd_help

class Emotes:
    """Twitch Emotes commands."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO("data/emotes/settings.json","load")
        self.emote_list = {}
        self.available_emotes = fileIO("data/emotes/available_emotes.json","load")

    def save_settings(self):
        fileIO("data/emotes/settings.json","save",self.settings)

    def _is_enabled(self,server):
        assert isinstance(server,discord.Server)
        if server.id not in self.settings:
            return False
        if not self.settings.get(server.id,False):
            return False
        return True

    @commands.group(pass_context=True)
    @checks.mod_or_permission(manage_messages=True)
    async def emoteset(self,ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx):
            #TODO server-specific settings

    @emoteset.command(name="enabled",pass_context=True)
    async def _emoteset_enabled(self,ctx,setting : bool):
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {}
        self.settings[server.id]["ENABLED"] = bool(setting)
        self.save_settings()
        if setting:
            await self.bot.reply("emotes are now enabled.")
        else:
            await self.bot.reply("emotes are now disabled.")

    def _write_image(self, chan_id, name, image_data):
        #Assume channel folder already exists
        with open('data/emotes/{}/{}'.format(chan_id,name)) as f:
            f.write(image_data)

    async def _add_emote(self,server,chan_id):
        assert isinstance(server,discord.Server)
        if chan_id == -1:
            return
        if not os.path.exists("data/emotes/{}".format(chan_id)):
            os.makedirs("data/emotes/{}".format(chan_id))
        for emote in self.emote_list:
            if chan_id == emote.get("emoticon_set",-1):
                url = emote.get("url","")
                name = emote.get("regex","")
                file_name = url.split('/')[-1]
                if url == "" or name == "":
                    continue
                try:
                    async with aiohttp.get(url) as r:
                        image = await r.content.read()
                except Exception as e:
                    print("Huh, I have no idea what errors aiohttp throws.")
                    print("This is one of them:")
                    print(e)
                    print(dir(e))
                    print("------")
                        self._write_image(chan_id,file_name,image)
                    if server.id not in self.available_emotes:
                        self.available_emotes[server.id] = {}
                    if name not in self.available_emotes[server.id]:
                        self.available_emotes[server.id] = {
                                                            "name":name,
                                                            "file_name":file_name,
                                                            "chan_id":chan_id
                                                        }

    @commands.command(pass_context=True)
    async def emote(self,ctx,emote_name:str):
        server = ctx.message.server
        if not self._is_enabled(server.id):
            await self.bot.say("Emotes are not enabled on this server.")
            return
        server_emotes = self.available_emotes[server.id]
        if emote_name in server_emotes:
            await self.bot.say("This server already has '{}'".format(emote_name))
            return
        for emote in self.emote_list:
            if emote_name == emote.get("regex",""):
                chan_id = emote.get("emoticon_set",-1)
                if chan_id == -1:
                    await self.bot.say("Yeah, something failed, try again later?")
                    return
                await self._add_emotes(server,chan_id)
                await self.bot.say("'{}' and other channel emotes added.")
                return

    async def check_messages(self, message):
        if message.server.id not in self.settings:
            return
        if not self._is_enabled(message.server):
            return

def check_folders():
    if not os.path.exists("data/emotes"):
        print("Creating data/emotes folder...")
        os.makedirs("data/emotes")

def check_files():
    f = "data/emotes/settings.json"
    if not fileIO(f, "check"):
        print("Creating empty settings.json...")
        fileIO(f, "save", {})

    f = "data/emotes/available_emotes.json"
    if not fileIO(f, "check"):
        print("Creating empty available_emotes.json...")
        fileIO(f, "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = Emotes(bot)
    n.update_emote_list()
    bot.add_listener(n.check_messages, "on_message")
    bot.add_cog(n)