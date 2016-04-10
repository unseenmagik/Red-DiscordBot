from discord.ext import commands
import requests
import aiohttp
import asyncio
from .utils import checks


class Status:
    "A Status cog"

    def __init__(self, bot):
        self.statuscount = 0
        self.statusurl = "http://status.squid.chat/api/v1/"
        self.statusapi = "8WDS0ZyAOJTQ2AOolquE"
        self.payload = {'id': 1, 'value': self.statuscount}
        self.header = {'X-Cachet-Token': self.statusapi}
        self.bot = bot

    @commands.command(no_pm=True, pass_context=True, hidden=True)
    @checks.is_owner()
    async def setcount(self, ctx, count: int):
        """DEBUG COMMAND"""
        self.statuscount = count
        await self.bot.say("done")

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def getcount(self, ctx):
        """DEBUG"""
        await self.bot.say("```{}```".format(self.statuscount))

    @commands.command(no_pm=True, pass_context=True, hidden=True)
    @checks.is_owner()
    async def sendpayload(self, ctx):
        """DEBUG COMMAND"""
        await self.tick()
        await self.bot.say("Done")

    async def start_timer(self):
        while "Status" in self.bot.cogs:
            await asyncio.sleep(60)
            await self.tick()

    async def tick(self):
        self.payload = {'id': 1, 'value': self.statuscount}
        self.header = {'X-Cachet-Token': self.statusapi}
        with aiohttp.ClientSession() as session:
            async with session.post(self.statusurl + 'metrics/1/points',
                                    data=self.payload,
                                    headers=self.header) as r:
                await r.release()
        self.statuscount = 0

    async def count(self, command, ctx):
        self.statuscount += 1


def setup(bot):
    n = Status(bot)
    bot.add_listener(n.start_timer, "on_ready")
    bot.add_listener(n.count, "on_command")
    bot.add_cog(n)
