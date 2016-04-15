import squid.utils as utils
import squid.registry as registry
import squid.i18n as i18n
from squid.version import version

import optparse
import os
import sys
import parser
import time
import sys
import shutil
import textwrap

#
#
#   Squid - A bot based on discord.py written by tekulvw (Will)
#
#    
#    #
#    # 
#    # Originally forked from Twentysix
#    #    https://github.com/Twentysix26/Red-DiscordBot
#    # 
#    #
#    
#


description = """
Squid - An upgraded version of Red-DiscordBot rewritten by tekulvw (Will)
"""

async def send_cmd_help(ctx):
    if ctx.invoked_subcommand:
        pages = bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
        for page in pages:
            await bot.send_message(ctx.message.channel, page)
    else:
        pages = bot.formatter.format_help_for(ctx, ctx.command)
        for page in pages:
            await bot.send_message(ctx.message.channel, page)

def user_allowed(message):

    author = message.author

    mod = bot.get_cog('Mod')
    
    if mod is not None:
        if settings.owner == author.id:
            return True
        if not message.channel.is_private:
            server = message.server
            names = (settings.get_server_admin(server),settings.get_server_mod(server))
            if None not in map(lambda name: discord.utils.get(author.roles,name=name),names):
                return True

        if author.id in mod.blacklist_list:
            return False

        if mod.whitelist_list:
            if author.id not in mod.whitelist_list:
                return False

        if not message.channel.is_private:
            if message.server.id in mod.ignore_list["SERVERS"]:
                return False

            if message.channel.id in mod.ignore_list["CHANNELS"]:
                return False
        return True
    else:
        return True

if __name__ == '__main__':
    parser = optparse.OptionParser(usage='Usage: %prog [options] configFile',
                                   version='Squidbot %s running on Python%s' %
                                   (version, sys.version))
    parser.add_option('-n', '--nick', action='store',
                      dest='nick', default='',
                      help='nick the bot should use')
    parser.add_option('', '--debug', action='store_true', dest='debug',
                      help='Determines whether some extra debugging stuff '
                      'will be logged in this script.')

    (options, args) = parser.parse_args()

    if os.name == 'posix':
        if os.getuid() == 0 or os.geteuid() == 0:
            sys.stderr.write('Yeah I\'m not gonna let you run as root.')

    if len(args) > 1:
        parser.error("""Only one configuration file should be specified.""")
    elif not args:
        parser.error(utils.str.normalizeWhitespace("""It seems you've given me
        no configuration file.  If you do have a configuration file, be sure to
        specify the filename.  If you don't have a configuration file, read
        docs/GETTING_STARTED and follow the instructions."""))
    else:
        registryFilename = args.pop()
        try:
            # The registry *MUST* be opened before importing log or conf.
            i18n.getLocaleFromRegistryFilename(registryFilename)
            registry.open_registry(registryFilename)
            shutil.copy(registryFilename, registryFilename + '.bak')
        except registry.InvalidRegistryFile as e:
            s = '%s in %s.  Please fix this error and start squidbot again.' % \
                (e, registryFilename)
            s = textwrap.fill(s)
            sys.stderr.write(s)
            sys.stderr.write(os.linesep)
            raise
            sys.exit(-1)
        except EnvironmentError as e:
            sys.stderr.write(str(e))
            sys.stderr.write(os.linesep)
            sys.exit(-1)
    try:
        import squid.log as log
    except registry.InvalidRegistryValue as e:
        # This is raised here because squidbot.log imports squidbot.conf.
        name = e.value._name
        errmsg = textwrap.fill('%s: %s' % (name, e),
                               width=78, subsequent_indent=' '*len(name))
        sys.stderr.write(errmsg)
        sys.stderr.write(os.linesep)
        sys.stderr.write('Please fix this error in your configuration file '
                         'and restart your bot.')
        sys.stderr.write(os.linesep)
        sys.exit(-1)

    import squid.conf as conf
    i18n.import_conf()
    import squid.bot as bot

    if not os.path.exists(conf.squidbot.directories.log()):
        os.mkdir(conf.squidbot.directories.log())
    if not os.path.exists(conf.squidbot.directories.data()):
        os.mkdir(conf.squidbot.directories.data())
    if not os.path.exists(conf.squidbot.directories.data.tmp()):
        os.mkdir(conf.squidbot.directories.tmp())

    userdataFilename = os.path.join(conf.squidbot.directories.conf(),
                                    'userdata.conf')
    # Let's open this now since we've got our directories setup.
    if not os.path.exists(userdataFilename):
        fd = open(userdataFilename, 'w')
        fd.write('\n')
        fd.close()
    registry.open_registry(userdataFilename)

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main())
    except discord.LoginFailure:
        log.error("Invalid login credentials!")
        sys.exit(-1)
    except Exception:
        log.exception("Some odd error occurred.")
        loop.run_until_complete(bot.logout())
    finally:
        loop.close()
