###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008-2009,2011, James McCoy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import os
import sys
import time
import socket

import discord
from . import registry, utils
from .version import version
from .i18n import PluginInternationalization
_ = PluginInternationalization()

###
# *** The following variables are affected by command-line options.  They are
#     not registry variables for a specific reason.  Do *not* change these to
#     registry variables without first consulting people smarter than yourself.
###

###
# daemonized: This determines whether or not the bot has been daemonized
#             (i.e., set to run in the background).  Obviously, this defaults
#             to False.  A command-line option for obvious reasons.
###
daemonized = False

###
# allowDefaultOwner: True if squidbot.capabilities is allowed not to include
#                    '-owner' -- that is, if all users should be automatically
#                    recognized as owners.  That would suck, hence we require a
#                    command-line option to allow this stupidity.
###
allowDefaultOwner = False

###
# Here we replace values in other modules as appropriate.
###
utils.web.defaultHeaders['User-agent'] = \
                         'Mozilla/5.0 (Compatible; Squidbot %s)' % version

###
# The standard registry.
###
squidbot = registry.Group()
squidbot.setName('squidbot')

def registerGroup(Group, name, group=None, **kwargs):
    if kwargs:
        group = registry.Group(**kwargs)
    return Group.register(name, group)

def registerGlobalValue(group, name, value):
    value.serverValue = False
    return group.register(name, value)

def registerServerValue(group, name, value):
    value._supplyDefault = True
    value.serverValue = True
    g = group.register(name, value)
    gname = g._name.lower()
    print("-----4 {}".format(gname))
    print("-----4.5", value)
    for name in registry._cache.keys():
        if name.lower().startswith(gname) and len(gname) < len(name):
            name = name[len(gname)+1:] # +1 for .
            print("-----5", name)
            parts = registry.split(name)
            print("-----6", parts)
            if len(parts) == 1 and parts[0]:
                # This gets the server values so they always persist.
                g.get(parts[0])()

def registerPlugin(name, currentValue=None, public=True):
    group = registerGlobalValue(squidbot.plugins, name,
        registry.Boolean(False, _("""Determines whether this plugin is loaded
         by default."""), showDefault=False))
    squidbot.plugins().add(name)
    registerGlobalValue(group, 'public',
        registry.Boolean(public, _("""Determines whether this plugin is
        publicly visible.""")))
    if currentValue is not None:
        squidbot.plugins.get(name).setValue(currentValue)
    registerGroup(users.plugins, name)
    return group

def get(group, server=None):
    if group.serverValue and \
       server is not None:
        return group.get(server)()
    else:
        return group()

###
# The user info registry.
###
users = registry.Group()
users.setName('users')
registerGroup(users, 'plugins', orderAlphabetically=True)

def registerUserValue(group, name, value):
    assert group._name.startswith('users')
    value._supplyDefault = True
    group.register(name, value)

registerGlobalValue(squidbot, 'nick',
    registry.String('squidbot', _("""Determines the bot's default nick.""")))

registerGlobalValue(squidbot, 'owner',
    registry.String('squidbot', _("""Owner ID used to identify an owner on
    Discord network.""")))

registerGlobalValue(squidbot, 'email',
    registry.String('squidbot', _("""Email used to login."""),private=True))

registerGlobalValue(squidbot, 'password',
    registry.String('squidbot', _("""Password used to login."""),private=True))

###
# Reply/error tweaking.
###
print("-----2")
registerGroup(squidbot, 'reply')

registerGroup(squidbot.reply, 'format')
registerServerValue(squidbot.reply.format, 'url',
    registry.String('<%s>', _("""Determines how urls should be formatted.""")))

def url(s):
    if s:
        return squidbot.reply.format.url() % s
    else:
        return ''
utils.str.url = url

registerServerValue(squidbot.reply.format, 'time',
    registry.String('%Y-%m-%dT%H:%M:%S%z', _("""Determines how timestamps
    printed for human reading should be formatted. Refer to the Python
    documentation for the time module to see valid formatting characters for
    time formats.""")))

def timestamp(t):
    if t is None:
        t = time.time()
    if isinstance(t, float) or isinstance(t, int):
        t = time.localtime(t)
    format = get(squidbot.reply.format.time, dynamic.server)
    return time.strftime(format, t)
utils.str.timestamp = timestamp

registerGroup(squidbot.reply.format.time, 'elapsed')
registerServerValue(squidbot.reply.format.time.elapsed, 'short',
    registry.Boolean(False, _("""Determines whether elapsed times will be given
    as "1 day, 2 hours, 3 minutes, and 15 seconds" or as "1d 2h 3m 15s".""")))

originalTimeElapsed = utils.timeElapsed
def timeElapsed(*args, **kwargs):
    kwargs['short'] = squidbot.reply.format.time.elapsed.short()
    return originalTimeElapsed(*args, **kwargs)
utils.timeElapsed = timeElapsed

registerGlobalValue(squidbot.reply, 'maximumLength',
    registry.Integer(2000, _("""Determines the absolute maximum length of
    the bot's reply -- no reply will be passed through the bot with a length
    greater than this.""")))

print("-----3")

registerServerValue(squidbot.reply, 'mores',
    registry.Boolean(True, _("""Determines whether the bot will break up long
    messages into chunks and allow users to use  the 'more' command to get the
    remaining chunks.""")))

print("-----1")

registerServerValue(squidbot.reply.mores, 'maximum',
    registry.PositiveInteger(50, _("""Determines what the maximum number of
    chunks (for use with the 'more' command) will be.""")))

registerServerValue(squidbot.reply.mores, 'length',
    registry.NonNegativeInteger(0, _("""Determines how long individual chunks
    will be.  If set to 0, uses our super-tweaked,
    get-the-most-out-of-an-individual-message default.""")))

registerServerValue(squidbot.reply.mores, 'instant',
    registry.PositiveInteger(1, _("""Determines how many mores will be sent
    instantly (i.e., without the use of the more command, immediately when
    they are formed).  Defaults to 1, which means that a more command will be
    required for all but the first chunk.""")))

registerServerValue(squidbot.reply, 'oneToOne',
    registry.Boolean(True, _("""Determines whether the bot will send
    multi-message replies in a single message. This defaults to True 
    in order to prevent the bot from flooding. If this is set to False
    the bot will send multi-message replies on multiple lines.""")))

registerServerValue(squidbot.reply, 'whenNotCommand',
    registry.Boolean(True, _("""Determines whether the bot will reply with an
    error message when it is addressed but not given a valid command.  If this
    value is False, the bot will remain silent, as long as no other plugins
    override the normal behavior.""")))

registerGroup(squidbot.reply, 'error')
registerGlobalValue(squidbot.reply.error, 'detailed',
    registry.Boolean(False, _("""Determines whether error messages that result
    from bugs in the bot will show a detailed error message (the uncaught
    exception) or a generic error message.""")))

registerServerValue(squidbot.reply.error, 'inPrivate',
    registry.Boolean(False, _("""Determines whether the bot will send error
    messages to users in private.  You might want to do this in order to keep
    server traffic to minimum.  This can be used in combination with
    squidbot.reply.error.withNotice.""")))

registerServerValue(squidbot.reply.error, 'noCapability',
    registry.Boolean(False, _("""Determines whether the bot will *not* provide
    details in the error
    message to users who attempt to call a command for which they do not have
    the necessary capability.  You may wish to make this True if you don't want
    users to understand the underlying security system preventing them from
    running certain commands.""")))

registerServerValue(squidbot.reply, 'inPrivate',
    registry.Boolean(False, _("""Determines whether the bot will reply
     privately when replying in a server, rather than replying to the whole
     server.""")))

registerServerValue(squidbot.reply, 'withNickPrefix',
    registry.Boolean(True, _("""Determines whether the bot will always prefix
     the user's nick to its reply to that user's command.""")))

registerServerValue(squidbot.reply, 'whenNotAddressed',
    registry.Boolean(False, _("""Determines whether the bot should attempt to
    reply to all messages even if they don't address it (either via its nick
    or a prefix character).  If you set this to True, you almost certainly want
    to set squidbot.reply.whenNotCommand to False.""")))

registerServerValue(squidbot.reply, 'requireServerCommandsToBeSentInServer',
    registry.Boolean(False, _("""Determines whether the bot will allow you to
    send server-related commands outside of that server.  Sometimes people
    find it confusing if a server-related command (like Filter.outfilter)
    changes the behavior of the server but was sent outside the server
    itself.""")))

registerServerValue(squidbot, 'alwaysJoinOnInvite',
    registry.Boolean(False, _("""Determines whether the bot will always join a
    server when it's invited.  If this value is False, the bot will only join
    a server if the user inviting it has the 'admin' capability (or if it's
    explicitly told to join the server using the Admin.join command).""")))

registerServerValue(squidbot.reply, 'showSimpleSyntax',
    registry.Boolean(False, _("""squidbot normally replies with the full help
    whenever a user misuses a command.  If this value is set to True, the bot
    will only reply with the syntax of the command (the first line of the
    help) rather than the full help.""")))

class ValidPrefixChars(registry.String):
    """Value must contain only ~!@#$%^&*()_-+=[{}]\\|'\";:,<.>/?"""
    def setValue(self, v):
        if any([x not in '`~!@#$%^&*()_-+=[{}]\\|\'";:,<.>/?' for x in v]):
            self.error()
        registry.String.setValue(self, v)

registerGroup(squidbot.reply, 'whenAddressedBy')
registerServerValue(squidbot.reply.whenAddressedBy, 'chars',
    ValidPrefixChars('', _("""Determines what prefix characters the bot will
    reply to.  A prefix character is a single character that the bot will use
    to determine what messages are addressed to it; when there are no prefix
    characters set, it just uses its nick.  Each character in this string is
    interpreted individually; you can have multiple prefix chars
    simultaneously, and if any one of them is used as a prefix the bot will
    assume it is being addressed.""")))

registerServerValue(squidbot.reply.whenAddressedBy, 'strings',
    registry.SpaceSeparatedSetOfStrings([], _("""Determines what strings the
    bot will reply to when they are at the beginning of the message.  Whereas
    prefix.chars can only be one character (although there can be many of
    them), this variable is a space-separated list of strings, so you can
    set something like '@@ ??' and the bot will reply when a message is
    prefixed by either @@ or ??.""")))

registerServerValue(squidbot.reply.whenAddressedBy, 'nick',
    registry.Boolean(True, _("""Determines whether the bot will reply when
    people address it by its nick, rather than with a prefix character.""")))

registerServerValue(squidbot.reply.whenAddressedBy.nick, 'atEnd',
    registry.Boolean(False, _("""Determines whether the bot will reply when
    people address it by its nick at the end of the message, rather than at
    the beginning.""")))

registerServerValue(squidbot.reply.whenAddressedBy, 'nicks',
    registry.SpaceSeparatedSetOfStrings([], _("""Determines what extra nicks
    the bot will always respond to when addressed by, even if its current nick
    is something else.""")))

###
# Replies
###
registerGroup(squidbot, 'replies')

registerServerValue(squidbot.replies, 'success',
    registry.NormalizedString(_("""The operation succeeded."""),
    _("""Determines what message the bot replies with when a command succeeded.
    If this configuration variable is empty, no success message will be
    sent.""")))

registerServerValue(squidbot.replies, 'error',
    registry.NormalizedString(_("""An error has occurred and has been logged.
    Please contact this bot's administrator for more information."""), _("""
    Determines what error message the bot gives when it wants to be
    ambiguous.""")))

registerServerValue(squidbot.replies, 'errorOwner',
    registry.NormalizedString(_("""An error has occurred and has been logged.
    Check the logs for more information."""), _("""Determines what error
    message the bot gives to the owner when it wants to be ambiguous.""")))

registerServerValue(squidbot.replies, 'incorrectAuthentication',
    registry.NormalizedString(_("""Your hostmask doesn't match or your password
    is wrong."""), _("""Determines what message the bot replies with when
     someone tries to use a command that requires being identified or having a
    password and neither credential is correct.""")))

# XXX: This should eventually check that there's one and only one %s here.
registerServerValue(squidbot.replies, 'noUser',
    registry.NormalizedString(_("""I can't find %s in my user
    database.  If you didn't give a user name, then I might not know what your
    user is, and you'll need to identify before this command might work."""),
    _("""Determines what error message the bot replies with when someone tries
    to accessing some information on a user the bot doesn't know about.""")))

registerServerValue(squidbot.replies, 'notRegistered',
    registry.NormalizedString(_("""You must be registered to use this command.
    If you are already registered, you must either identify (using the identify
    command) or add a hostmask matching your current hostmask (using the
    "hostmask add" command)."""), _("""Determines what error message the bot
    replies with when someone tries to do something that requires them to be
    registered but they're not currently recognized.""")))

registerServerValue(squidbot.replies, 'noCapability',
    registry.NormalizedString(_("""You don't have the %s capability.  If you
    think that you should have this capability, be sure that you are identified
    before trying again.  The 'whoami' command can tell you if you're
    identified."""), _("""Determines what error message is given when the bot
    is telling someone they aren't cool enough to use the command they tried to
    use.""")))

registerServerValue(squidbot.replies, 'genericNoCapability',
    registry.NormalizedString(_("""You're missing some capability you need.
    This could be because you actually possess the anti-capability for the
    capability that's required of you, or because the server provides that
    anti-capability by default, or because the global capabilities include
    that anti-capability.  Or, it could be because the server or
    squidbot.capabilities.default is set to False, meaning that no commands are
    allowed unless explicitly in your capabilities.  Either way, you can't do
    what you want to do."""),
    _("""Determines what generic error message is given when the bot is telling
    someone that they aren't cool enough to use the command they tried to use,
    and the author of the code calling errorNoCapability didn't provide an
    explicit capability for whatever reason.""")))

registerServerValue(squidbot.replies, 'requiresPrivacy',
    registry.NormalizedString(_("""That operation cannot be done in a
    server."""), _("""Determines what error messages the bot sends to people
    who try to do things in a server that really should be done in
    private.""")))

registerServerValue(squidbot.replies, 'possibleBug',
    registry.NormalizedString(_("""This may be a bug.  If you think it is,
    please file a bug report at
    <https://github.com/tekulvw/Squid-Discordbot/issues>."""),
    _("""Determines what message the bot sends when it thinks you've
    encountered a bug that the developers don't know about.""")))
###
# End squidbot.replies.
###

registerGlobalValue(squidbot, 'upkeepInterval',
    registry.PositiveInteger(3600, _("""Determines the number of seconds
    between running the upkeep function that flushes (commits) open databases,
    collects garbage, and records some useful statistics at the debugging
     level.""")))

registerGlobalValue(squidbot, 'flush',
    registry.Boolean(True, _("""Determines whether the bot will periodically
    flush data and configuration files to disk.  Generally, the only time
    you'll want to set this to False is when you want to modify those
    configuration files by hand and don't want the bot to flush its current
    version over your modifications.  Do note that if you change this to False
    inside the bot, your changes won't be flushed.  To make this change
    permanent, you must edit the registry yourself.""")))


###
# squidbot.commands.  For stuff relating to commands.
###
registerGroup(squidbot, 'commands')

class ValidQuotes(registry.Value):
    """Value must consist solely of \", ', and ` characters."""
    def setValue(self, v):
        if [c for c in v if c not in '"`\'']:
            self.error()
        super(ValidQuotes, self).setValue(v)

    def __str__(self):
        return str(self.value)

registerServerValue(squidbot.commands, 'quotes',
    ValidQuotes('"', _("""Determines what characters are valid for quoting
    arguments to commands in order to prevent them from being tokenized.
    """)))
# This is a GlobalValue because bot owners should be able to say, "There will
# be no nesting at all on this bot."  Individual servers can just set their
# brackets to the empty string.
registerGlobalValue(squidbot.commands, 'nested',
    registry.Boolean(True, _("""Determines whether the bot will allow nested
    commands, which rule.  You definitely should keep this on.""")))
registerGlobalValue(squidbot.commands.nested, 'maximum',
    registry.PositiveInteger(10, _("""Determines what the maximum number of
    nested commands will be; users will receive an error if they attempt
    commands more nested than this.""")))

class ValidBrackets(registry.OnlySomeStrings):
    validStrings = ('', '[]', '<>', '{}', '()')

registerServerValue(squidbot.commands.nested, 'brackets',
    ValidBrackets('[]', _("""squidbot allows you to specify what brackets
    are used for your nested commands.  Valid sets of brackets include
    [], <>, {}, and ().  [] has strong historical motivation, but <> or
    () might be slightly superior because they cannot occur in a nick.
    If this string is empty, nested commands will not be allowed in this
    server.""")))

registerServerValue(squidbot.commands.nested, 'pipeSyntax',
    registry.Boolean(False, _("""squidbot allows nested commands. Enabling this
    option will allow nested commands with a syntax similar to UNIX pipes, for
    example: 'bot: foo | bar'.""")))

registerGroup(squidbot.commands, 'defaultPlugins',
    orderAlphabetically=True, help=_("""Determines what commands have default
    plugins set, and which plugins are set to be the default for each of those
    commands."""))
registerGlobalValue(squidbot.commands.defaultPlugins, 'importantPlugins',
    registry.SpaceSeparatedSetOfStrings(
        ['Admin', 'Server', 'Config', 'Misc', 'Owner', 'User'],
        _("""Determines what plugins automatically get precedence over all
        other plugins when selecting a default plugin for a command.  By
        default, this includes the standard loaded plugins.  You probably
        shouldn't change this if you don't know what you're doing; if you do
        know what you're doing, then also know that this set is
        case-sensitive.""")))

# squidbot.commands.disabled moved to callbacks for canonicalName.

###
# squidbot.abuse.  For stuff relating to abuse of the bot.
###
registerGroup(squidbot, 'abuse')
registerGroup(squidbot.abuse, 'flood')
registerGlobalValue(squidbot.abuse.flood, 'interval',
    registry.PositiveInteger(60, _("""Determines the interval used for
    the history storage.""")))
registerGlobalValue(squidbot.abuse.flood, 'command',
    registry.Boolean(True, _("""Determines whether the bot will defend itself
    against command-flooding.""")))
registerGlobalValue(squidbot.abuse.flood.command, 'maximum',
    registry.PositiveInteger(12, _("""Determines how many commands users are
    allowed per minute.  If a user sends more than this many commands in any
    60 second period, they will be ignored for
    squidbot.abuse.flood.command.punishment seconds.""")))
registerGlobalValue(squidbot.abuse.flood.command, 'punishment',
    registry.PositiveInteger(300, _("""Determines how many seconds the bot
    will ignore users who flood it with commands.""")))
registerGlobalValue(squidbot.abuse.flood.command, 'notify',
    registry.Boolean(True, _("""Determines whether the bot will notify people
    that they're being ignored for command flooding.""")))

registerGlobalValue(squidbot.abuse.flood.command, 'invalid',
    registry.Boolean(True, _("""Determines whether the bot will defend itself
    against invalid command-flooding.""")))
registerGlobalValue(squidbot.abuse.flood.command.invalid, 'maximum',
    registry.PositiveInteger(5, _("""Determines how many invalid commands users
    are allowed per minute.  If a user sends more than this many invalid
    commands in any 60 second period, they will be ignored for
    squidbot.abuse.flood.command.invalid.punishment seconds.  Typically, this
    value is lower than squidbot.abuse.flood.command.maximum, since it's far
    less likely (and far more annoying) for users to flood with invalid
    commands than for them to flood with valid commands.""")))
registerGlobalValue(squidbot.abuse.flood.command.invalid, 'punishment',
    registry.PositiveInteger(600, _("""Determines how many seconds the bot
    will ignore users who flood it with invalid commands.  Typically, this
    value is higher than squidbot.abuse.flood.command.punishment, since it's far
    less likely (and far more annoying) for users to flood with invalid
    commands than for them to flood with valid commands.""")))
registerGlobalValue(squidbot.abuse.flood.command.invalid, 'notify',
    registry.Boolean(True, _("""Determines whether the bot will notify people
    that they're being ignored for invalid command flooding.""")))

###
# squidbot.directories, for stuff relating to directories.
###

# XXX This shouldn't make directories willy-nilly.  As it is now, if it's
#     configured, it'll still make the default directories, I think.
class Directory(registry.String):
    def __call__(self):
        # ??? Should we perhaps always return an absolute path here?
        v = super(Directory, self).__call__()
        if not os.path.exists(v):
            os.mkdir(v)
        return v

    def dirize(self, filename):
        myself = self()
        if os.path.isabs(filename):
            filename = os.path.abspath(filename)
            selfAbs = os.path.abspath(myself)
            commonPrefix = os.path.commonprefix([selfAbs, filename])
            filename = filename[len(commonPrefix):]
        elif not os.path.isabs(myself):
            if filename.startswith(myself):
                filename = filename[len(myself):]
        filename = filename.lstrip(os.path.sep) # Stupid os.path.join!
        return os.path.join(myself, filename)

class DataFilename(registry.String):
    def __call__(self):
        v = super(DataFilename, self).__call__()
        dataDir = squidbot.directories.data()
        if not v.startswith(dataDir):
            v = os.path.basename(v)
            v = os.path.join(dataDir, v)
        self.setValue(v)
        return v

class DataFilenameDirectory(DataFilename, Directory):
    def __call__(self):
        v = DataFilename.__call__(self)
        v = Directory.__call__(self)
        return v

registerGroup(squidbot, 'directories')
registerGlobalValue(squidbot.directories, 'conf',
    Directory('conf', _("""Determines what directory configuration data is
    put into.""")))
registerGlobalValue(squidbot.directories, 'data',
    Directory('data', _("""Determines what directory data is put into.""")))
registerGlobalValue(squidbot.directories, 'backup',
    Directory('backup', _("""Determines what directory backup data is put
    into. Set it to /dev/null to disable backup (it is a special value,
    so it also works on Windows and systems without /dev/null).""")))
registerGlobalValue(squidbot.directories.data, 'tmp',
    DataFilenameDirectory('tmp', _("""Determines what directory temporary files
    are put into.""")))

utils.file.AtomicFile.default.tmpDir = squidbot.directories.data.tmp
utils.file.AtomicFile.default.backupDir = squidbot.directories.backup

registerGlobalValue(squidbot.directories, 'plugins',
    registry.CommaSeparatedListOfStrings([], _("""Determines what directories
    the bot will look for plugins in.  Accepts a comma-separated list of
    strings.
    This means that to add another directory, you can nest the former value and
    add a new one.  E.g. you can say: bot: 'config squidbot.directories.plugins
    [config squidbot.directories.plugins], newPluginDirectory'.""")))

registerGlobalValue(squidbot, 'plugins',
    registry.SpaceSeparatedSetOfStrings([], _("""Determines what plugins will
    be loaded."""), orderAlphabetically=True))
registerGlobalValue(squidbot.plugins, 'alwaysLoadImportant',
    registry.Boolean(True, _("""Determines whether the bot will always load
    important plugins (Admin, Server, Config, Misc, Owner, and User)
    regardless of what their configured state is.  Generally, if these plugins
    are configured not to load, you didn't do it on purpose, and you still
    want them to load.  Users who don't want to load these plugins are smart
    enough to change the value of this variable appropriately :)""")))

###
# squidbot.databases.  For stuff relating to squidbot's databases (duh!)
###
class Databases(registry.SpaceSeparatedListOfStrings):
    def __call__(self):
        v = super(Databases, self).__call__()
        if not v:
            v = ['anydbm', 'dbm', 'cdb', 'flat', 'pickle']
            if 'sqlite' in sys.modules:
                v.insert(0, 'sqlite')
            if 'sqlite3' in sys.modules:
                v.insert(0, 'sqlite3')
            if 'sqlalchemy' in sys.modules:
                v.insert(0, 'sqlalchemy')
        return v

    def serialize(self):
        return ' '.join(self.value)

registerGlobalValue(squidbot, 'databases',
    Databases(['flat'], _("""Determines what databases are available for use. If this
    value is not configured (that is, if its value is empty) then sane defaults
    will be provided.""")))

registerGroup(squidbot.databases, 'ignores')
registerGlobalValue(squidbot.databases.ignores, 'filename',
    registry.String('ignores.conf', _("""Determines what filename will be used
    for the ignores database.  This file will go into the directory specified
    by the squidbot.directories.conf variable.""")))

registerGroup(squidbot.databases, 'servers')
registerGlobalValue(squidbot.databases.servers, 'filename',
    registry.String('servers.conf', _("""Determines what filename will be used
    for the servers database.  This file will go into the directory specified
    by the squidbot.directories.conf variable.""")))

# TODO This will need to do more in the future (such as making sure link.allow
# will let the link occur), but for now let's just leave it as this.
class ServerSpecific(registry.Boolean):
    def getServerLink(self, server):
        serverSpecific = squidbot.databases.plugins.serverSpecific
        servers = [server]
        def hasLinkServer(server):
            if not get(serverSpecific, server):
                lserver = get(serverSpecific.link, server)
                if not get(serverSpecific.link.allow, lserver):
                    return False
                return server != lserver
            return False
        lserver = server
        while hasLinkServer(lserver):
            lserver = get(serverSpecific.link, lserver)
            if lserver not in servers:
                servers.append(lserver)
            else:
                # Found a cyclic link.  We'll just use the current server
                lserver = server
                break
        return lserver

registerGroup(squidbot.databases, 'plugins')

registerServerValue(squidbot.databases.plugins, 'serverSpecific',
    ServerSpecific(True, _("""Determines whether database-based plugins that
    can be server-specific will be so.  This can be overridden by individual
    servers.  Do note that the bot needs to be restarted immediately after
    changing this variable or your db plugins may not work for your server;
    also note that you may wish to set
    squidbot.databases.plugins.serverSpecific.link appropriately if you wish
    to share a certain server's databases globally.""")))


class CDB(registry.Boolean):
    def connect(self, filename):
        from . import cdb
        basename = os.path.basename(filename)
        journalName = squidbot.directories.data.tmp.dirize(basename+'.journal')
        return cdb.open_db(filename, 'c',
                        journalName=journalName,
                        maxmods=self.maximumModifications())

registerGroup(squidbot.databases, 'types')
registerGlobalValue(squidbot.databases.types, 'cdb', CDB(True, _("""Determines
    whether CDB databases will be allowed as a database implementation.""")))
registerGlobalValue(squidbot.databases.types.cdb, 'maximumModifications',
    registry.Probability(0.5, _("""Determines how often CDB databases will have
    their modifications flushed to disk.  When the number of modified records
    is greater than this fraction of the total number of records, the database
    will be entirely flushed to disk.""")))

# XXX Configuration variables for dbi, sqlite, flat, mysql, etc.

registerGlobalValue(squidbot, 'pidFile',
    registry.String('', _("""Determines what file the bot should write its PID
    (Process ID) to, so you can kill it more easily.  If it's left unset (as is
    the default) then no PID file will be written.  A restart is required for
    changes to this variable to take effect.""")))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79: