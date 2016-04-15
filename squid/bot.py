import discord
from discord.ext import commands
import asyncio
import time
import imp
import sys
import traceback
from . import registry, log, conf
import os
from .utils.iter import any, all
from .pluginutils import checks

bot = commands.Bot(command_prefix=["~"])

async def login():
    await bot.login(_email,_password)

async def connect():
    await bot.connect()

async def main():
    await bot.login(_email,_password)
    await bot.connect()

def run():
    load_defaults(bot)
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main())
    except discord.LoginFailure:
        log.error("Invalid login credentials!")
        sys.exit(-1)
    except Exception:
        log.error("Some odd error occurred.")
        loop.run_until_complete(bot.logout())
    finally:
        loop.close()

def debug_info():
    log.debug('Email: {}'.format(_email))
    log.debug('Prefixes: {}'.format(_prefix_chars))

async def send_cmd_help(ctx):
    if ctx.invoked_subcommand:
        pages = bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
        for page in pages:
            await bot.send_message(ctx.message.channel, page)
    else:
        pages = bot.formatter.format_help_for(ctx, ctx.command)
        for page in pages:
            await bot.send_message(ctx.message.channel, page)

@bot.event
async def on_ready():
    users = str(len([m for m in bot.get_all_members()]))
    servers = str(len(bot.servers))
    channels = str(len([c for c in bot.get_all_channels()]))
    log.info('------')
    log.info(bot.user.name + " is now online.")
    log.info('------')
    log.info("Connected to:")
    log.info(servers + " servers")
    log.info(channels + " channels")
    log.info(users + " users")
    log.info("{0} active cogs with {1} commands\n".format(str(len(bot.cogs)), str(len(bot.commands))))
    uptime = int(time.perf_counter())

@bot.event
async def on_command(ctx,command):
    pass

@bot.event
async def on_message(message):
    #TODO Flood stuff
    if addressed(message):
        await bot.process_commands(message)
@bot.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.MissingRequiredArgument):
        await send_cmd_help(ctx)
    elif isinstance(error, commands.BadArgument):
        await send_cmd_help(ctx)
    elif isinstance(error, commands.CheckFailure):
        log.debug("{} on {} just tried to do '{}'".format(ctx.message.author,
                    ctx.message.server,ctx.message.content))
        await bot.send_message(ctx.message.author,"You likely don't have permissions for that.")

def _addressed(nick, msg, prefixChars=None, nicks=None,
              prefixStrings=None, whenAddressedByNick=None,
              whenAddressedByNickAtEnd=None):
    def get(group):
        if server_id in [server.id for server in bot.servers]:
            group = group.get(server_id)
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
    nick = bot.user.name
    return _addressed(nick, msg, **kwargs)

def _loadPlugin(name):
    files = []
    pluginDirs = conf.squidbot.directories.plugins()[:]
    for dir in pluginDirs:
        try:
            files.extend(os.listdir(dir))
        except EnvironmentError:
            log.warning('Invalid plugin directory: %s; removing.', dir)
            conf.squidbot.directories.plugins().remove(dir)
    if name not in files:
        log.warning('Module not found')
        raise RuntimeError
    moduleInfo = imp.find_module(name,pluginDirs)
    try:
        module = imp.load_module(name,*moduleInfo)
    except:
        sys.modules.pop(name, None)
        keys = list(sys.modules.keys())
        for key in keys:
            if key.startswith(name + '.'):
                sys.modules.pop(key)
        raise
    return module

def load_defaults(bot):
    for name, value in conf.squidbot.plugins.getValues(fullNames=False):
        try:
            _loadPlugin(name)
        except:
            log.warning('Could not load {}'.format(name))

@checks.is_owner()
@bot.command()
async def load(name : str):
    try:
        module = _loadPlugin(name)
        module.configure()
        bot.load_extension(module.__name__)
    except Exception as e:
        traceback.print_exc()
        log.warning('Found module "{}" but couldn\'t load it.'.format(name))
        await bot.say('{}: {}'.format(type(e).__name__,e))
    else:
        await bot.say('Module enabled.')

@bot.command(check=checks.is_owner,pass_context=True)
async def debug(ctx, *, code : str):
    """Evaluates code"""
    code = code.strip('` ')
    python = '```py\n{}\n```'
    result = None

    try:
        result = eval(code)
    except Exception as e:
        await bot.say(python.format(type(e).__name__ + ': ' + str(e)))
        return

    if asyncio.iscoroutine(result):
        result = await result

    result = python.format(result)
    if not ctx.message.channel.is_private:
        email = conf.squidbot.email()
        password = conf.squidbot.password()
        censor = (email, password)
        r = "[EXPUNGED]"
        for w in censor:
            result = result.replace(w, r)
            result = result.replace(w.lower(), r)
            result = result.replace(w.upper(), r)
    await bot.say(result)

@checks.is_owner()
@bot.command()
async def shutdown():
    await bot.logout()

_email = conf.squidbot.email()
_password = conf.squidbot.password()

_prefix_chars = conf.squidbot.reply.whenAddressedBy.chars()
_prefix_strings = conf.squidbot.reply.whenAddressedBy.strings()
_respond_to_nick = conf.squidbot.reply.whenAddressedBy.nick()

formatter = commands.HelpFormatter(show_check_failure=True)
pm_help = None
command_prefix=_prefix_chars

debug_info()