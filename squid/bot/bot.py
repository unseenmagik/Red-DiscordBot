import discord
from discord.ext import commands
import asyncio
from . import registry, log, conf

class Bot(commands.Bot):
    def __init__(self,*args,**kwargs):
        super(Bot, self).__init__(*args,**kwargs)
        self._email = conf.squidbot.email()
        self._password = conf.squidbot.password()

        self._prefix_chars = conf.squidbot.reply.whenAddressedBy.chars()
        self._prefix_strings = conf.squidbot.reply.whenAddressedBy.strings()
        self._respond_to_nick = conf.squidbot.reply.whenAddressedBy.nick()

        self.formatter = commands.HelpFormatter(show_check_failure=True)
        self.pm_help = None
        self.command_prefix=self._prefix_chars

        self.debug_info()

    def debug_info(self):
        log.debug('Email: {}'.format(self._email))
        log.debug('Prefixes: {}'.format(self._prefix_chars))

    @self.event
    async def on_ready():
        users = str(len([m for m in self.get_all_members()]))
        servers = str(len(self.servers))
        channels = str(len([c for c in self.get_all_channels()]))
        log.info('------')
        log.info(self.user.name + " is now online.")
        log.info('------')
        log.info("Connected to:")
        log.info(servers + " servers")
        log.info(channels + " channels")
        log.info(users + " users")
        log.info("\n{0} active cogs with {1} commands\n".format(str(len(self.cogs)), str(len(self.commands))))
        self.uptime = int(time.perf_counter())

    async def login(self):
        await super(Bot,self).login(self._email,self._password)

    @self.event
    async def on_command(ctx,command):
        pass

    @self.event
    async def on_message(self,message):
        #TODO Flood stuff
        #prefix stuff
        log.debug('Made it to on message.')
        if self.addressed(message):
            await self.process_commands(message)

    @self.event
    async def on_command_error(error, ctx):
        if isinstance(error, commands.MissingRequiredArgument):
            await send_cmd_help(ctx)
        elif isinstance(error, commands.BadArgument):
            await send_cmd_help(ctx)
        elif isinstance(error, commands.CheckFailure):
            await self.send_message(ctx.message.author,"You likely don't have permissions for that.")

    def _addressed(nick, msg, prefixChars=None, nicks=None,
                  prefixStrings=None, whenAddressedByNick=None,
                  whenAddressedByNickAtEnd=None):
        def get(group):
            if server_id in [server.id for server in bot.servers]:
                group = group.get(target)
            return group()
        def stripPrefixStrings(payload):
            for prefixString in prefixStrings:
                if payload.startswith(prefixString):
                    payload = payload[len(prefixString):].lstrip()
            return payload

        server_id = msg.server.id if msg.server else None
        channel = msg.channel
        author = msg.author
        payload = msg.content
        if not payload or payload == '':
            return False
        if prefixChars is None:
            prefixChars = get(conf.squidbot.reply.whenAddressedBy.chars)
        if whenAddressedByNick is None:
            whenAddressedByNick = get(conf.squidbot.reply.whenAddressedBy.nick)
        if whenAddressedByNickAtEnd is None:
            r = conf.squidbot.reply.whenAddressedBy.nick.atEnd
            whenAddressedByNickAtEnd = get(r)
        if prefixStrings is None:
            prefixStrings = get(conf.squidbot.reply.whenAddressedBy.strings)
        # We have to check this before nicks -- try "@google squidbot" with squidbot
        # and whenAddressedBy.nick.atEnd on to see why.
        if any(payload.startswith, prefixStrings):
            return True
        elif payload[0] in prefixChars:
            return True
        if nicks is None:
            nicks = get(conf.squidbot.reply.whenAddressedBy.nicks)
            nicks = list(map(str.lower, nicks))
        else:
            nicks = list(nicks) # Just in case.
        nicks.insert(0, str.lower(nick))
        # Ok, let's see if it's a private message.
        if not server_id:
            return True
        # Ok, not private.  Does it start with our nick?
        elif whenAddressedByNick:
            for nick in nicks:
                lowered = payload.lower()
                if lowered.startswith(nick):
                    try:
                        (maybeNick, rest) = payload.split(None, 1)
                        if maybeNick == nick:
                            return True
                        else:
                            continue
                    except ValueError: # split didn't work.
                        continue
                elif whenAddressedByNickAtEnd and lowered.endswith(nick):
                    rest = payload[:-len(nick)]
                    possiblePayload = rest.rstrip(' \t,;')
                    if possiblePayload != rest:
                        # There should be some separator between the nick and the
                        # previous alphanumeric character.
                        return True
        if get(conf.squidbot.reply.whenNotAddressed):
            return True
        else:
            return False

    def addressed(msg, **kwargs):
        """If msg is addressed to me, return True."""
        nick = self.bot.user.name
        return _addressed(nick, msg, **kwargs)

bot = Bot()