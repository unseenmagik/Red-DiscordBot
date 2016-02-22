import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
import os

class Tickets:
    def __init__(self,bot):
        self.bot = bot
        self.tickets = fileIO("data/tickets/tickets.json","load")

    def _get_ticket(self):
        if len(self.tickets) > 0:
            ticket = self.tickets[0]
            for idnum in ticket:
                ret = ticket[idnum].get("name","no_name")+": "+ticket[idnum].get("message","no_message")
            self.tickets = self.tickets[1:]
            fileIO("data/tickets/tickets.json","save",self.tickets)
            return ret
        else:
            return "No more tickets!"

    def _add_question(self,author,message):
        self.tickets.append({author.id:{"name":author.name,"message":message}})
        fileIO("data/tickets/tickets.json","save",self.tickets)

    @commands.command(aliases=["nt"],pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def nextticket(self,ctx):
        await self.bot.send_message(ctx.message.author,self._get_ticket())

    @commands.command(pass_context=True)
    async def ticket(self,ctx,*message):
        """Adds ticket.

           Example: !ticket The quick brown fox? -> adds ticket"""
        message = " ".join(message)
        self._add_question(ctx.message.author,message)
        await self.bot.say("Question added.")

def check_folder():
    if not os.path.exists("data/tickets"):
        print("Creating data/tickets folder...")
        os.makedirs("data/tickets")

def check_file():
    tickets = []

    f = "data/tickets/tickets.json"
    if not fileIO(f, "check"):
        print("Creating default tickets's tickets.json...")
        fileIO(f, "save", tickets)

def setup(bot):
    check_folder()
    check_file()
    n = Tickets(bot)
    bot.add_cog(n)