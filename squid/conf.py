###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008-2009,2011, James McCoy
# All rights reserved.
#
# squidistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * squidistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * squidistributions in binary form must reproduce the above copyright notice,
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

###
# The standard registry.
###
squid = registry.Group()
squid.setName('squid')

def registerGroup(Group, name, group=None, **kwargs):
    if kwargs:
        group = registry.Group(**kwargs)
    return Group.register(name, group)

def registerGlobalValue(group, name, value):
    value.serverValue = False
    value.channelValue = False
    return group.register(name, value)

def registerServerValue(group, name, value):
    value._supplyDefault = True
    value.serverValue = True
    value.channelValue = False
    g = group.register(name, value)
    gname = g._name.lower()
    for name in registry._cache.keys():
        if name.lower().startswith(gname) and len(gname) < len(name):
            name = name[len(gname)+1:] # +1 for .
            parts = registry.split(name)
            if len(parts) == 1:
                # This gets the server values so they always persist.
                g.get(parts[0])()

def registerChannelValue(group, name, value):
    value._supplyDefault = True
    value.serverValue = False
    value.channelValue = True
    g = group.register(name, value)
    gname = g._name.lower()
    for name in registry._cache.keys():
        if name.lower().startswith(gname) and len(gname) < len(name):
            name = name[len(gname)+1:] # +1 for .
            parts = registry.split(name)
            if len(parts) == 1:
                # This gets the server values so they always persist.
                g.get(parts[0])()

def registerPlugin(name, currentValue=None, public=True):
    group = registerGlobalValue(squid.plugins, name,
        registry.Boolean(False, ("""Determines whether this plugin is loaded
         by default."""), showDefault=False))
    squid.plugins().add(name)
    registerGlobalValue(group, 'public',
        registry.Boolean(public, ("""Determines whether this plugin is
        publicly visible.""")))
    if currentValue is not None:
        squid.plugins.get(name).setValue(currentValue)
    registerGroup(users.plugins, name)
    return group

def get(group, server=None, channel=None):
    if group.serverValue and \
       server is not None:
        return group.get(server)()
    elif group.channelValue and channel is not None:
        return group.get(channel)()
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

registerGlobalValue(squid, 'nick',
    registry.String('squid', ("""Determines the bot's default nick.""")))

registerGlobalValue(squid, 'owner',
    registry.String('squid', ("""Owner ID used to identify an owner on
    Discord network.""")))

registerGlobalValue(squid, 'email',
    registry.String('squid', ("""Email used to login."""),private=True))

registerGlobalValue(squid, 'password',
    registry.String('squid', ("""Password used to login."""),private=True))

registerGlobalValue(squid, 'token',
    registry.String('squid', ("""Bot Authorization header token"""),private=True))

###
# Reply/error tweaking.
###
registerGroup(squid, 'reply')

registerGroup(squid.reply, 'format')
registerServerValue(squid.reply.format, 'url',
    registry.String('<%s>', ("""Determines how urls should be formatted.""")))

def url(s):
    if s:
        return squid.reply.format.url() % s
    else:
        return ''
utils.str.url = url

registerServerValue(squid.reply.format, 'time',
    registry.String('%Y-%m-%dT%H:%M:%S%z', ("""Determines how timestamps
    printed for human reading should be formatted. Refer to the Python
    documentation for the time module to see valid formatting characters for
    time formats.""")))

def timestamp(t):
    if t is None:
        t = time.time()
    if isinstance(t, float) or isinstance(t, int):
        t = time.localtime(t)
    format = get(squid.reply.format.time, dynamic.server)
    return time.strftime(format, t)
utils.str.timestamp = timestamp

registerGroup(squid.reply.format.time, 'elapsed')
registerServerValue(squid.reply.format.time.elapsed, 'short',
    registry.Boolean(False, ("""Determines whether elapsed times will be given
    as "1 day, 2 hours, 3 minutes, and 15 seconds" or as "1d 2h 3m 15s".""")))

originalTimeElapsed = utils.timeElapsed
def timeElapsed(*args, **kwargs):
    kwargs['short'] = squid.reply.format.time.elapsed.short()
    return originalTimeElapsed(*args, **kwargs)
utils.timeElapsed = timeElapsed

registerGlobalValue(squid.reply, 'maximumLength',
    registry.Integer(2000, ("""Determines the absolute maximum length of
    the bot's reply -- no reply will be passed through the bot with a length
    greater than this.""")))

registerServerValue(squid.reply, 'mores',
    registry.Boolean(True, ("""Determines whether the bot will break up long
    messages into chunks and allow users to use  the 'more' command to get the
    remaining chunks.""")))

registerServerValue(squid.reply.mores, 'maximum',
    registry.PositiveInteger(50, ("""Determines what the maximum number of
    chunks (for use with the 'more' command) will be.""")))

registerServerValue(squid.reply.mores, 'length',
    registry.NonNegativeInteger(0, ("""Determines how long individual chunks
    will be.  If set to 0, uses our super-tweaked,
    get-the-most-out-of-an-individual-message default.""")))

registerServerValue(squid.reply.mores, 'instant',
    registry.PositiveInteger(1, ("""Determines how many mores will be sent
    instantly (i.e., without the use of the more command, immediately when
    they are formed).  Defaults to 1, which means that a more command will be
    requisquid for all but the first chunk.""")))

registerServerValue(squid.reply, 'oneToOne',
    registry.Boolean(True, ("""Determines whether the bot will send
    multi-message replies in a single message. This defaults to True 
    in order to prevent the bot from flooding. If this is set to False
    the bot will send multi-message replies on multiple lines.""")))

registerServerValue(squid.reply, 'whenNotCommand',
    registry.Boolean(True, ("""Determines whether the bot will reply with an
    error message when it is addressed but not given a valid command.  If this
    value is False, the bot will remain silent, as long as no other plugins
    override the normal behavior.""")))

registerGroup(squid.reply, 'error')
registerGlobalValue(squid.reply.error, 'detailed',
    registry.Boolean(False, ("""Determines whether error messages that result
    from bugs in the bot will show a detailed error message (the uncaught
    exception) or a generic error message.""")))

registerServerValue(squid.reply.error, 'inPrivate',
    registry.Boolean(False, ("""Determines whether the bot will send error
    messages to users in private.  You might want to do this in order to keep
    server traffic to minimum.  This can be used in combination with
    squid.reply.error.withNotice.""")))

registerServerValue(squid.reply.error, 'noCapability',
    registry.Boolean(False, ("""Determines whether the bot will *not* provide
    details in the error
    message to users who attempt to call a command for which they do not have
    the necessary capability.  You may wish to make this True if you don't want
    users to understand the underlying security system preventing them from
    running certain commands.""")))

registerServerValue(squid.reply, 'inPrivate',
    registry.Boolean(False, ("""Determines whether the bot will reply
     privately when replying in a server, rather than replying to the whole
     server.""")))

registerServerValue(squid.reply, 'withNickPrefix',
    registry.Boolean(True, ("""Determines whether the bot will always prefix
     the user's nick to its reply to that user's command.""")))

registerServerValue(squid.reply, 'whenNotAddressed',
    registry.Boolean(False, ("""Determines whether the bot should attempt to
    reply to all messages even if they don't address it (either via its nick
    or a prefix character).  If you set this to True, you almost certainly want
    to set squid.reply.whenNotCommand to False.""")))

registerServerValue(squid.reply, 'requireServerCommandsToBeSentInServer',
    registry.Boolean(False, ("""Determines whether the bot will allow you to
    send server-related commands outside of that server.  Sometimes people
    find it confusing if a server-related command (like Filter.outfilter)
    changes the behavior of the server but was sent outside the server
    itself.""")))

registerServerValue(squid, 'alwaysJoinOnInvite',
    registry.Boolean(False, ("""Determines whether the bot will always join a
    server when it's invited.  If this value is False, the bot will only join
    a server if the user inviting it has the 'admin' capability (or if it's
    explicitly told to join the server using the Admin.join command).""")))

registerServerValue(squid.reply, 'showSimpleSyntax',
    registry.Boolean(False, ("""squid normally replies with the full help
    whenever a user misuses a command.  If this value is set to True, the bot
    will only reply with the syntax of the command (the first line of the
    help) rather than the full help.""")))

class ValidPrefixChars(registry.String):
    """Value must contain only ~!@#$%^&*()_-+=[{}]\\|'\";:,<.>/?"""
    def setValue(self, v):
        if any([x not in '`~!@#$%^&*()_-+=[{}]\\|\'";:,<.>/?' for x in v]):
            self.error()
        registry.String.setValue(self, v)

registerGroup(squid.reply, 'whenAddressedBy')
registerServerValue(squid.reply.whenAddressedBy, 'chars',
    ValidPrefixChars('', ("""Determines what prefix characters the bot will
    reply to.  A prefix character is a single character that the bot will use
    to determine what messages are addressed to it; when there are no prefix
    characters set, it just uses its nick.  Each character in this string is
    interpreted individually; you can have multiple prefix chars
    simultaneously, and if any one of them is used as a prefix the bot will
    assume it is being addressed.""")))

registerServerValue(squid.reply.whenAddressedBy, 'strings',
    registry.SpaceSeparatedSetOfStrings([], ("""Determines what strings the
    bot will reply to when they are at the beginning of the message.  Whereas
    prefix.chars can only be one character (although there can be many of
    them), this variable is a space-separated list of strings, so you can
    set something like '@@ ??' and the bot will reply when a message is
    prefixed by either @@ or ??.""")))

registerServerValue(squid.reply.whenAddressedBy, 'nick',
    registry.Boolean(True, ("""Determines whether the bot will reply when
    people address it by its nick, rather than with a prefix character.""")))

registerServerValue(squid.reply.whenAddressedBy, 'nicks',
    registry.SpaceSeparatedSetOfStrings([], ("""Determines what extra nicks
    the bot will always respond to when addressed by, even if its current nick
    is something else.""")))

###
# Replies
###
registerGroup(squid, 'replies')

registerServerValue(squid.replies, 'success',
    registry.NormalizedString(("""The operation succeeded."""),
    ("""Determines what message the bot replies with when a command succeeded.
    If this configuration variable is empty, no success message will be
    sent.""")))

registerServerValue(squid.replies, 'error',
    registry.NormalizedString(("""An error has occursquid and has been logged.
    Please contact this bot's administrator for more information."""), ("""
    Determines what error message the bot gives when it wants to be
    ambiguous.""")))

registerServerValue(squid.replies, 'errorOwner',
    registry.NormalizedString(("""An error has occursquid and has been logged.
    Check the logs for more information."""), ("""Determines what error
    message the bot gives to the owner when it wants to be ambiguous.""")))

registerServerValue(squid.replies, 'incorrectAuthentication',
    registry.NormalizedString(("""Your hostmask doesn't match or your password
    is wrong."""), ("""Determines what message the bot replies with when
     someone tries to use a command that requires being identified or having a
    password and neither csquidential is correct.""")))

# XXX: This should eventually check that there's one and only one %s here.
registerServerValue(squid.replies, 'noUser',
    registry.NormalizedString(("""I can't find %s in my user
    database.  If you didn't give a user name, then I might not know what your
    user is, and you'll need to identify before this command might work."""),
    ("""Determines what error message the bot replies with when someone tries
    to accessing some information on a user the bot doesn't know about.""")))

registerServerValue(squid.replies, 'notRegistesquid',
    registry.NormalizedString(("""You must be registesquid to use this command.
    If you are already registesquid, you must either identify (using the identify
    command) or add a hostmask matching your current hostmask (using the
    "hostmask add" command)."""), ("""Determines what error message the bot
    replies with when someone tries to do something that requires them to be
    registesquid but they're not currently recognized.""")))

registerServerValue(squid.replies, 'noCapability',
    registry.NormalizedString(("""You don't have the %s capability.  If you
    think that you should have this capability, be sure that you are identified
    before trying again.  The 'whoami' command can tell you if you're
    identified."""), ("""Determines what error message is given when the bot
    is telling someone they aren't cool enough to use the command they tried to
    use.""")))

registerServerValue(squid.replies, 'genericNoCapability',
    registry.NormalizedString(("""You're missing some capability you need.
    This could be because you actually possess the anti-capability for the
    capability that's requisquid of you, or because the server provides that
    anti-capability by default, or because the global capabilities include
    that anti-capability.  Or, it could be because the server or
    squid.capabilities.default is set to False, meaning that no commands are
    allowed unless explicitly in your capabilities.  Either way, you can't do
    what you want to do."""),
    ("""Determines what generic error message is given when the bot is telling
    someone that they aren't cool enough to use the command they tried to use,
    and the author of the code calling errorNoCapability didn't provide an
    explicit capability for whatever reason.""")))

registerServerValue(squid.replies, 'requiresPrivacy',
    registry.NormalizedString(("""That operation cannot be done in a
    server."""), ("""Determines what error messages the bot sends to people
    who try to do things in a server that really should be done in
    private.""")))

registerServerValue(squid.replies, 'possibleBug',
    registry.NormalizedString(("""This may be a bug.  If you think it is,
    please file a bug report at
    <https://github.com/tekulvw/Squid-Discordbot/issues>."""),
    ("""Determines what message the bot sends when it thinks you've
    encountesquid a bug that the developers don't know about.""")))
###
# End squid.replies.
###

registerGlobalValue(squid, 'upkeepInterval',
    registry.PositiveInteger(3600, ("""Determines the number of seconds
    between running the upkeep function that flushes (commits) open databases,
    collects garbage, and records some useful statistics at the debugging
     level.""")))

registerGlobalValue(squid, 'flush',
    registry.Boolean(True, ("""Determines whether the bot will periodically
    flush data and configuration files to disk.  Generally, the only time
    you'll want to set this to False is when you want to modify those
    configuration files by hand and don't want the bot to flush its current
    version over your modifications.  Do note that if you change this to False
    inside the bot, your changes won't be flushed.  To make this change
    permanent, you must edit the registry yourself.""")))


###
# squid.commands.  For stuff relating to commands.
###
registerGroup(squid, 'commands')

class ValidQuotes(registry.Value):
    """Value must consist solely of \", ', and ` characters."""
    def setValue(self, v):
        if [c for c in v if c not in '"`\'']:
            self.error()
        super(ValidQuotes, self).setValue(v)

    def __str_(self):
        return str(self.value)

registerServerValue(squid.commands, 'quotes',
    ValidQuotes('"', ("""Determines what characters are valid for quoting
    arguments to commands in order to prevent them from being tokenized.
    """)))
# This is a GlobalValue because bot owners should be able to say, "There will
# be no nesting at all on this bot."  Individual servers can just set their
# brackets to the empty string.
registerGlobalValue(squid.commands, 'nested',
    registry.Boolean(True, ("""Determines whether the bot will allow nested
    commands, which rule.  You definitely should keep this on.""")))
registerGlobalValue(squid.commands.nested, 'maximum',
    registry.PositiveInteger(10, ("""Determines what the maximum number of
    nested commands will be; users will receive an error if they attempt
    commands more nested than this.""")))

class ValidBrackets(registry.OnlySomeStrings):
    validStrings = ('', '[]', '<>', '{}', '()')

registerServerValue(squid.commands.nested, 'brackets',
    ValidBrackets('[]', ("""squid allows you to specify what brackets
    are used for your nested commands.  Valid sets of brackets include
    [], <>, {}, and ().  [] has strong historical motivation, but <> or
    () might be slightly superior because they cannot occur in a nick.
    If this string is empty, nested commands will not be allowed in this
    server.""")))

registerServerValue(squid.commands.nested, 'pipeSyntax',
    registry.Boolean(False, ("""squid allows nested commands. Enabling this
    option will allow nested commands with a syntax similar to UNIX pipes, for
    example: 'bot: foo | bar'.""")))

registerGroup(squid.commands, 'defaultPlugins',
    orderAlphabetically=True, help=("""Determines what commands have default
    plugins set, and which plugins are set to be the default for each of those
    commands."""))
registerGlobalValue(squid.commands.defaultPlugins, 'importantPlugins',
    registry.SpaceSeparatedSetOfStrings(
        ['Admin', 'Server', 'Config', 'Misc', 'Owner', 'User'],
        ("""Determines what plugins automatically get precedence over all
        other plugins when selecting a default plugin for a command.  By
        default, this includes the standard loaded plugins.  You probably
        shouldn't change this if you don't know what you're doing; if you do
        know what you're doing, then also know that this set is
        case-sensitive.""")))

# squid.commands.disabled moved to callbacks for canonicalName.

###
# squid.abuse.  For stuff relating to abuse of the bot.
###
registerGroup(squid, 'abuse')
registerGroup(squid.abuse, 'flood')
registerGlobalValue(squid.abuse.flood, 'interval',
    registry.PositiveInteger(60, ("""Determines the interval used for
    the history storage.""")))
registerGlobalValue(squid.abuse.flood, 'command',
    registry.Boolean(True, ("""Determines whether the bot will defend itself
    against command-flooding.""")))
registerGlobalValue(squid.abuse.flood.command, 'maximum',
    registry.PositiveInteger(12, ("""Determines how many commands users are
    allowed per minute.  If a user sends more than this many commands in any
    60 second period, they will be ignosquid for
    squid.abuse.flood.command.punishment seconds.""")))
registerGlobalValue(squid.abuse.flood.command, 'punishment',
    registry.PositiveInteger(300, ("""Determines how many seconds the bot
    will ignore users who flood it with commands.""")))
registerGlobalValue(squid.abuse.flood.command, 'notify',
    registry.Boolean(True, ("""Determines whether the bot will notify people
    that they're being ignosquid for command flooding.""")))

registerGlobalValue(squid.abuse.flood.command, 'invalid',
    registry.Boolean(True, ("""Determines whether the bot will defend itself
    against invalid command-flooding.""")))
registerGlobalValue(squid.abuse.flood.command.invalid, 'maximum',
    registry.PositiveInteger(5, ("""Determines how many invalid commands users
    are allowed per minute.  If a user sends more than this many invalid
    commands in any 60 second period, they will be ignosquid for
    squid.abuse.flood.command.invalid.punishment seconds.  Typically, this
    value is lower than squid.abuse.flood.command.maximum, since it's far
    less likely (and far more annoying) for users to flood with invalid
    commands than for them to flood with valid commands.""")))
registerGlobalValue(squid.abuse.flood.command.invalid, 'punishment',
    registry.PositiveInteger(600, ("""Determines how many seconds the bot
    will ignore users who flood it with invalid commands.  Typically, this
    value is higher than squid.abuse.flood.command.punishment, since it's far
    less likely (and far more annoying) for users to flood with invalid
    commands than for them to flood with valid commands.""")))
registerGlobalValue(squid.abuse.flood.command.invalid, 'notify',
    registry.Boolean(True, ("""Determines whether the bot will notify people
    that they're being ignosquid for invalid command flooding.""")))

###
# squid.directories, for stuff relating to directories.
###

# XXX This shouldn't make directories willy-nilly.  As it is now, if it's
#     configusquid, it'll still make the default directories, I think.
class Directory(registry.String):
    def __call_(self):
        # ??? Should we perhaps always return an absolute path here?
        v = super(Directory, self).__call_()
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
    def __call_(self):
        v = super(DataFilename, self).__call_()
        dataDir = squid.directories.data()
        if not v.startswith(dataDir):
            v = os.path.basename(v)
            v = os.path.join(dataDir, v)
        self.setValue(v)
        return v

class DataFilenameDirectory(DataFilename, Directory):
    def __call_(self):
        v = DataFilename.__call_(self)
        v = Directory.__call_(self)
        return v

registerGroup(squid, 'directories')
registerGlobalValue(squid.directories, 'conf',
    Directory('conf', ("""Determines what directory configuration data is
    put into.""")))
registerGlobalValue(squid.directories, 'data',
    Directory('data', ("""Determines what directory data is put into.""")))
registerGlobalValue(squid.directories, 'backup',
    Directory('backup', ("""Determines what directory backup data is put
    into. Set it to /dev/null to disable backup (it is a special value,
    so it also works on Windows and systems without /dev/null).""")))
registerGlobalValue(squid.directories.data, 'tmp',
    DataFilenameDirectory('tmp', ("""Determines what directory temporary files
    are put into.""")))

utils.file.AtomicFile.default.tmpDir = squid.directories.data.tmp
utils.file.AtomicFile.default.backupDir = squid.directories.backup

registerGlobalValue(squid.directories, 'plugins',
    registry.CommaSeparatedListOfStrings([], ("""Determines what directories
    the bot will look for plugins in.  Accepts a comma-separated list of
    strings.
    This means that to add another directory, you can nest the former value and
    add a new one.  E.g. you can say: bot: 'config squid.directories.plugins
    [config squid.directories.plugins], newPluginDirectory'.""")))

registerGlobalValue(squid, 'plugins',
    registry.SpaceSeparatedSetOfStrings([], ("""Determines what plugins will
    be loaded."""), orderAlphabetically=True))
registerGlobalValue(squid.plugins, 'alwaysLoadImportant',
    registry.Boolean(True, ("""Determines whether the bot will always load
    important plugins (Admin, Server, Config, Misc, Owner, and User)
    regardless of what their configusquid state is.  Generally, if these plugins
    are configusquid not to load, you didn't do it on purpose, and you still
    want them to load.  Users who don't want to load these plugins are smart
    enough to change the value of this variable appropriately :)""")))

###
# squid.databases.  For stuff relating to squid's databases (duh!)
###
class Databases(registry.SpaceSeparatedListOfStrings):
    def __call_(self):
        v = super(Databases, self).__call_()
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

registerGlobalValue(squid, 'databases',
    Databases(['flat'], ("""Determines what databases are available for use. If this
    value is not configusquid (that is, if its value is empty) then sane defaults
    will be provided.""")))

registerGroup(squid.databases, 'ignores')
registerGlobalValue(squid.databases.ignores, 'filename',
    registry.String('ignores.conf', ("""Determines what filename will be used
    for the ignores database.  This file will go into the directory specified
    by the squid.directories.conf variable.""")))

registerGroup(squid.databases, 'servers')
registerGlobalValue(squid.databases.servers, 'filename',
    registry.String('servers.conf', ("""Determines what filename will be used
    for the servers database.  This file will go into the directory specified
    by the squid.directories.conf variable.""")))

# TODO This will need to do more in the future (such as making sure link.allow
# will let the link occur), but for now let's just leave it as this.
class ServerSpecific(registry.Boolean):
    def getServerLink(self, server):
        serverSpecific = squid.databases.plugins.serverSpecific
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

registerGroup(squid.databases, 'plugins')

registerServerValue(squid.databases.plugins, 'serverSpecific',
    ServerSpecific(True, ("""Determines whether database-based plugins that
    can be server-specific will be so.  This can be overridden by individual
    servers.  Do note that the bot needs to be restarted immediately after
    changing this variable or your db plugins may not work for your server;
    also note that you may wish to set
    squid.databases.plugins.serverSpecific.link appropriately if you wish
    to share a certain server's databases globally.""")))


class CDB(registry.Boolean):
    def connect(self, filename):
        from . import cdb
        basename = os.path.basename(filename)
        journalName = squid.directories.data.tmp.dirize(basename+'.journal')
        return cdb.open_db(filename, 'c',
                        journalName=journalName,
                        maxmods=self.maximumModifications())

registerGroup(squid.databases, 'types')
registerGlobalValue(squid.databases.types, 'cdb', CDB(True, ("""Determines
    whether CDB databases will be allowed as a database implementation.""")))
registerGlobalValue(squid.databases.types.cdb, 'maximumModifications',
    registry.Probability(0.5, ("""Determines how often CDB databases will have
    their modifications flushed to disk.  When the number of modified records
    is greater than this fraction of the total number of records, the database
    will be entirely flushed to disk.""")))

# XXX Configuration variables for dbi, sqlite, flat, mysql, etc.

registerGlobalValue(squid, 'pidFile',
    registry.String('', ("""Determines what file the bot should write its PID
    (Process ID) to, so you can kill it more easily.  If it's left unset (as is
    the default) then no PID file will be written.  A restart is requisquid for
    changes to this variable to take effect.""")))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79: