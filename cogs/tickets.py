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
        self.settings = fileIO("data/tickets/settings.json","load")

    @property
    def ticket_limit(self):
        return self.settings.get("TICKETS_PER_USER",0)

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

    def _get_number_tickets(self,author):
        idnum = author.id
        num = len([x for ticket in self.tickets for x in ticket if x == idnum])
        return num

    def _add_ticket(self,author,message):
        self.tickets.append({author.id:{"name":author.name,"message":message}})
        fileIO("data/tickets/tickets.json","save",self.tickets)

    @commands.command(aliases=["nt"],pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def nextticket(self,ctx):
        """Gets the next ticket"""
        await self.bot.send_message(ctx.message.author,self._get_ticket())

    @commands.command(pass_context=True)
    async def ticket(self,ctx,*,message):
        """Adds ticket.

           Example: !ticket The quick brown fox? -> adds ticket"""
        if self.ticket_limit != 0 and \
            self._get_number_tickets(ctx.message.author) >= self.ticket_limit:
            await self.bot.say("{}, you've reached the ticket limit!".format(ctx.message.author.mention))
            return
        self._add_ticket(ctx.message.author,message)
        await self.bot.say("{}, ticket added.".format(ctx.message.author.mention))

    @commands.command(aliases=['ct'])
    @checks.mod_or_permissions(manage_messages=True)
    async def cleartickets(self):
        """Clears all tickets"""
        self.tickets = []
        fileIO("data/tickets/tickets.json","save",self.tickets)
        await self.bot.say("Tickets cleared.")

    @commands.group(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def ticketset(self,ctx):
        """Ticket cog settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @ticketset.command(name="limit")
    async def tickets_per_user(self,num : int):
        """Limits the number of tickets a user can have."""
        if num < 0:
            send_cmd_help(self.tickets_per_user)
            return
        self.settings["TICKETS_PER_USER"] = num
        fileIO("data/tickets/settings.json","save",self.settings)
        await self.bot.say("Tickets per user set to {}".format(num))

def check_folder():
    if not os.path.exists("data/tickets"):
        print("Creating data/tickets folder...")
        os.makedirs("data/tickets")

def check_file():
    tickets = []
    settings = {"TICKETS_PER_USER":0,"REPLY_TO_CHANNEL":False}

    f = "data/tickets/tickets.json"
    if not fileIO(f, "check"):
        print("Creating default tickets's tickets.json...")
        fileIO(f, "save", tickets)

    f = "data/tickets/settings.json"
    if not fileIO(f, "check"):
        print("Creating default tickets's settings.json...")
        fileIO(f, "save", settings)

def setup(bot):
    check_folder()
    check_file()
    n = Tickets(bot)
    bot.add_cog(n)