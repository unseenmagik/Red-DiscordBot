#!/usr/bin/env python

###
# Copyright (c) 2003-2004, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
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

def error(s):
    sys.stderr.write(s)
    if not s.endswith(os.linesep):
        sys.stderr.write(os.linesep)
    sys.exit(-1)

if sys.version_info < (3, 4, 0):
    error('This program requires Python >= 3.4.0')

import re
import time
import pydoc
import pprint
import socket
import logging
import optparse

import squid.i18n as i18n
import squid.ansi as ansi
import squid.utils as utils
import squid.registry as registry
# squid.plugin, squid.log, and squid.conf will be imported later,
# because we need to set a language before loading the conf

import squid.questions as questions
from squid.questions import output, yn, anything, something, expect, getpass

def getPlugins(pluginDirs):
    plugins = set([])
    join = os.path.join
    for pluginDir in pluginDirs:
        try:
            for filename in os.listdir(pluginDir):
                fname = join(pluginDir, filename)
                if (filename.endswith('.py') or os.path.isdir(fname)) \
                   and filename[0].isupper():
                    plugins.add(os.path.splitext(filename)[0])
        except OSError:
            continue
    plugins.discard('Owner')
    plugins = list(plugins)
    plugins.sort()
    return plugins

def loadPlugin(name):
    import squid.plugin as plugin
    try:
        module = plugin.loadPluginModule(name)
        if hasattr(module, 'Class'):
            return module
        else:
            output("""That plugin loaded fine, but didn't seem to be a real
            Supybot plugin; there was no Class variable to tell us what class
            to load when we load the plugin.  We'll skip over it for now, but
            you can always add it later.""")
            return None
    except Exception as e:
        output("""We encountered a bit of trouble trying to load plugin %r.
        Python told us %r.  We'll skip over it for now, you can always add it
        later.""" % (name, utils.gen.exnToString(e)))
        return None

def describePlugin(module, showUsage):
    if module.__doc__:
        output(module.__doc__, unformatted=False)
    elif hasattr(module.Class, '__doc__'):
        output(module.Class.__doc__, unformatted=False)
    else:
        output("""Unfortunately, this plugin doesn't seem to have any
        documentation.  Sorry about that.""")
    if showUsage:
        if hasattr(module, 'example'):
            if yn('This plugin has a usage example.  '
                  'Would you like to see it?', default=False):
                pydoc.pager(module.example)
        else:
            output("""This plugin has no usage example.""")

def clearLoadedPlugins(plugins, pluginRegistry):
    for plugin in plugins:
        try:
            pluginKey = pluginRegistry.get(plugin)
            if pluginKey():
                plugins.remove(plugin)
        except registry.NonExistentRegistryEntry:
            continue

_windowsVarRe = re.compile(r'%(\w+)%')
def getDirectoryName(default, basedir=os.curdir, prompt=True):
    done = False
    while not done:
        if prompt:
            dir = something('What directory do you want to use?',
                           default=os.path.join(basedir, default))
        else:
            dir = os.path.join(basedir, default)
        orig_dir = dir
        dir = os.path.expanduser(dir)
        dir = _windowsVarRe.sub(r'$\1', dir)
        dir = os.path.expandvars(dir)
        dir = os.path.abspath(dir)
        try:
            os.makedirs(dir)
            done = True
        except OSError as e:
            # 17 is File exists for Linux (and likely other POSIX systems)
            # 183 is the same for Windows
            if e.args[0] == 17 or (os.name == 'nt' and e.args[0] == 183):
                done = True
            else:
                output("""Sorry, I couldn't make that directory for some
                reason.  The Operating System told me %s.  You're going to
                have to pick someplace else.""" % e)
                prompt = True
    return (dir, os.path.dirname(orig_dir))


def main():
    import squid.version as version
    parser = optparse.OptionParser(usage='Usage: %prog [options]',
                                   version='Supybot %s' % version.version)
    parser.add_option('', '--allow-root', action='store_true',
                      dest='allowRoot',
                      help='Determines whether the wizard will be allowed to '
                           'run as root.  You don\'t want this.  Don\'t do it.'
                           '  Even if you think you want it, you don\'t.  '
                           'You\'re probably dumb if you do this.')
    parser.add_option('', '--allow-home', action='store_true',
                      dest='allowHome',
                      help='Determines whether the wizard will be allowed to '
                           'run directly in the HOME directory. '
                           'You should not do this unless you want it to '
                           'create multiple files in your HOME directory.')
    parser.add_option('', '--no-network', action='store_false',
                      dest='network',
                      help='Determines whether the wizard will be allowed to '
                           'run without a network connection.')
    (options, args) = parser.parse_args()
    if os.name == 'posix':
        if (os.getuid() == 0 or os.geteuid() == 0) and not options.allowRoot:
            error('Please, don\'t run this as root.')
    if os.name == 'posix':
        if (os.getcwd() == os.path.expanduser('~')) and not options.allowHome:
            error('Please, don\'t run this in your HOME directory.')
    '''if os.path.isfile(os.path.join('scripts', 'squid-wizard')) or \
            os.path.isfile(os.path.join('..', 'scripts', 'squid-wizard')):
        print('')
        print('+------------------------------------------------------------+')
        print('| +--------------------------------------------------------+ |')
        print('| | Warning: It looks like you are running the wizard from | |')
        print('| | the Supybot source directory. This is not recommended. | |')
        print('| | Please press Ctrl-C and change to another directory.   | |')
        print('| +--------------------------------------------------------+ |')
        print('+------------------------------------------------------------+')
        print('')'''

    if args:
        parser.error('This program takes no non-option arguments.')
    output("""This is a wizard to help you start running squid.  What it
    will do is create the necessary config files based on the options you
    select here.  So hold on tight and be ready to be interrogated :)""")


    output("""First of all, we can bold the questions you're asked so you can
    easily distinguish the mostly useless blather (like this) from the
    questions that you actually have to answer.""")
    if yn('Would you like to try this bolding?', default=True):
        questions.useBold = True
        if not yn('Do you see this in bold?'):
            output("""Sorry, it looks like your terminal isn't ANSI compliant.
            Try again some other day, on some other terminal :)""")
            questions.useBold = False
        else:
            output("""Great!""")

    ###
    # Preliminary questions.
    ###
    output("""We've got some preliminary things to get out of the way before
    we can really start asking you questions that directly relate to what your
    bot is going to be like.""")

    # Advanced?
    output("""We want to know if you consider yourself an advanced Supybot
    user because some questions are just utterly boring and useless for new
    users.  Others might not make sense unless you've used Supybot for some
    time.""")
    advanced = yn('Are you an advanced Supybot user?', default=False)

    # Language?
    output("""This version of Supybot (known as Limnoria) includes another
    language. This can be changed at any time. You need to answer with a short
    id for the language, such as 'en', 'fr', 'it' (without the quotes). If
    you want to use English, just press enter.""")
    language = something('What language do you want to use?', default='en')

    class Empty:
        """This is a hack to allow the i18n to get the current language, before
        loading the conf module, before the conf module needs i18n to set the
        default strings."""
        def __call__(self):
            return self.value
    fakeConf = Empty()
    fakeConf.squid = Empty()
    fakeConf.squid.language = Empty()
    fakeConf.squid.language.value = language
    i18n.conf = fakeConf
    i18n.currentLocale = language
    i18n.reloadLocales()
    import squid.log as log
    log._stdoutHandler.setLevel(100) # *Nothing* gets through this!
    import squid.conf as conf
    i18n.import_conf() # It imports the real conf module
    import squid.plugin as plugin

    ### Directories.
    # We set these variables in cache because otherwise conf and log will
    # create directories for the default values, which might not be what the
    # user wants.
    if advanced:
        output("""Now we've got to ask you some questions about where some of
        your directories are (or, perhaps, will be :)).  If you're running this
        wizard from the directory you'll actually be starting your bot from and
        don't mind creating some directories in the current directory, then
        just don't give answers to these questions and we'll create the
        directories we need right here in this directory.""")

        # conf.squidbot.directories.log
        output("""Your bot will need to put its logs somewhere.  Do you have
        any specific place you'd like them?  If not, just press enter and we'll
        make a directory named "logs" right here.""")
        (logDir, basedir) = getDirectoryName('logs')
        conf.squidbot.directories.log.setValue(logDir)

        # conf.squidbot.directories.data
        output("""Your bot will need to put various data somewhere.  Things
        like databases, downloaded files, etc.  Do you have any specific place
        you'd like the bot to put these things?  If not, just press enter and
        we'll make a directory named "data" right here.""")
        (dataDir, basedir) = getDirectoryName('data', basedir=basedir)
        conf.squidbot.directories.data.setValue(dataDir)

        # conf.squidbot.directories.conf
        output("""Your bot must know where to find its configuration files.
        It'll probably only make one or two, but it's gotta have some place to
        put them.  Where should that place be?  If you don't care, just press
        enter and we'll make a directory right here named "conf" where it'll
        store its stuff. """)
        (confDir, basedir) = getDirectoryName('conf', basedir=basedir)
        conf.squidbot.directories.conf.setValue(confDir)

        # conf.squidbot.directories.backup
        output("""Your bot must know where to place backups of its conf and
        data files.  Where should that place be?  If you don't care, just press
        enter and we'll make a directory right here named "backup" where it'll
        store its stuff.""")
        (backupDir, basedir) = getDirectoryName('backup', basedir=basedir)
        conf.squidbot.directories.backup.setValue(backupDir)

        # pluginDirs
        output("""Your bot will also need to know where to find its plugins at.
        Of course, it already knows where the plugins that it came with are,
        but your own personal plugins that you write for will probably be
        somewhere else.""")
        pluginDirs = conf.squidbot.directories.plugins()
        output("""Currently, the bot knows about the following directories:""")
        output(format('%L', pluginDirs + [plugin._pluginsDir]))
        while yn('Would you like to add another plugin directory?  '
                 'Adding a local plugin directory is good style.',
                 default=True):
            (pluginDir, _) = getDirectoryName('plugins', basedir=basedir)
            if pluginDir not in pluginDirs:
                pluginDirs.append(pluginDir)
        conf.squidbot.directories.plugins.setValue(pluginDirs)
    else:
        output("""Your bot needs to create some directories in order to store
        the various log, config, and data files.""")
        basedir = something("""Where would you like to create these
                            directories?""", default=os.curdir)
        # conf.squidbot.directories.log
        (logDir, basedir) = getDirectoryName('logs',
                                             basedir=basedir, prompt=False)
        conf.squidbot.directories.log.setValue(logDir)
        # conf.squidbot.directories.data
        (dataDir, basedir) = getDirectoryName('data',
                                              basedir=basedir, prompt=False)
        conf.squidbot.directories.data.setValue(dataDir)
        # conf.squidbot.directories.conf
        (confDir, basedir) = getDirectoryName('conf',
                                              basedir=basedir, prompt=False)
        conf.squidbot.directories.conf.setValue(confDir)
        # conf.squidbot.directories.backup
        (backupDir, basedir) = getDirectoryName('backup',
                                                basedir=basedir, prompt=False)
        conf.squidbot.directories.backup.setValue(backupDir)
        # pluginDirs
        pluginDirs = conf.squidbot.directories.plugins()
        (pluginDir, _) = getDirectoryName('plugins',
                                          basedir=basedir, prompt=False)
        if pluginDir not in pluginDirs:
            pluginDirs.append(pluginDir)
        conf.squidbot.directories.plugins.setValue(pluginDirs)

    output("Good!  We're done with the directory stuff.")

    ###
    # Bot stuff
    ###
    output("""Now we're going to ask you things that actually relate to the
    bot you'll be running.""")

    # conf.squidbot.nick
    # Force the user into specifying a nick if it didn't have one already
    while True:
        nick = something('What nick would you like your bot to use?',
                         default=None)
        try:
            conf.squidbot.nick.set(nick)
            break
        except registry.InvalidRegistryValue:
            output("""That's not a valid nick.  Go ahead and pick another.""")

    output("""You're gonna need to set the owner's ID number for your bot.
    In order to find this you need to type `\@YourName` into Discord.""")
    owner = something("What is your ID?")
    conf.squidbot.owner.set(owner)

    email = something("""What is the email used to connect to your bot\'s
    account?""")
    conf.squidbot.email.set(email)

    # conf.squidbot.password
    output("""You'll need a password also in order to connect to your
    discord account.""")
    conf.squidbot.password.set(getpass())

    ###
    # Plugins
    ###
    def configurePlugin(module, advanced):
        if hasattr(module, 'configure'):
            output("""Beginning configuration for %s...""" %
                   module.Class.__name__)
            module.configure(advanced)
            print() # Blank line :)
            output("""Done!""")
        else:
            conf.registerPlugin(module.__name__, currentValue=True)

    plugins = getPlugins(pluginDirs + [plugin._pluginsDir])
    '''for s in ('Admin', 'User', 'Channel', 'Misc', 'Config', 'Utilities'):
        m = loadPlugin(s)
        if m is not None:
            configurePlugin(m, advanced)
        else:
            error('There was an error loading one of the core plugins that '
                  'under almost all circumstances are loaded.  Go ahead and '
                  'fix that error and run this script again.')'''
    clearLoadedPlugins(plugins, conf.squidbot.plugins)

    output("""Now we're going to run you through plugin configuration. There's
           a variety of plugins in squid by default, but you can create and
           add your own, of course. We'll allow you to take a look at the known
           plugins' descriptions and configure them
           if you like what you see.""")



    # bulk
    addedBulk = False
    if advanced and yn('Would you like to add plugins en masse first?'):
        addedBulk = True
        output(format("""The available plugins are: %L.""", plugins))
        output("""What plugins would you like to add?  If you've changed your
        mind and would rather not add plugins in bulk like this, just press
        enter and we'll move on to the individual plugin configuration.
        We suggest you to add Aka, Ctcp, Later, Network, Plugin, String,
        and Utilities""")
        massPlugins = anything('Separate plugin names by spaces or commas:')
        for name in re.split(r',?\s+', massPlugins):
            module = loadPlugin(name)
            if module is not None:
                configurePlugin(module, advanced)
                clearLoadedPlugins(plugins, conf.squidbot.plugins)

    # individual
    if yn('Would you like to look at plugins individually?'):
        output("""Next comes your opportunity to learn more about the plugins
        that are available and select some (or all!) of them to run in your
        bot.  Before you have to make a decision, of course, you'll be able to
        see a short description of the plugin and, if you choose, an example
        session with the plugin.  Let's begin.""")
        # until we get example strings again, this will default to false
        #showUsage =yn('Would you like the option of seeing usage examples?')
        showUsage = False
        name = expect('What plugin would you like to look at?',
                      plugins, acceptEmpty=True)
        while name:
            module = loadPlugin(name)
            if module is not None:
                describePlugin(module, showUsage)
                if yn('Would you like to load this plugin?', default=True):
                    configurePlugin(module, advanced)
                    clearLoadedPlugins(plugins, conf.squidbot.plugins)
            if not yn('Would you like add another plugin?'):
                break
            name = expect('What plugin would you like to look at?', plugins)

    ###
    # Sundry
    ###
    output("""Of course, when you're in a Discord Server you can address the bot
    by its nick and it will respond, if you give it a valid command (it may or
    may not respond, depending on what your config variable replyWhenNotCommand
    is set to).  But your bot can also respond to a short "prefix character,"
    so instead of saying "@bot do this," you can say, "!do this" and achieve
    the same effect.  Of course, you don't *have* to have a prefix char, but
    if the bot ends up participating significantly in your server, it'll ease
    things.""")
    if yn('Would you like to set the prefix char(s) for your bot?  ',
          default=True):
        output("""Enter any characters you want here, but be careful: they
        should be rare enough that people don't accidentally address the bot
        (simply because they'll probably be annoyed if they do address the bot
        on accident).  You can even have more than one.  I (jemfinch) am quite
        partial to @, but that's because I've been using it since my ocamlbot
        days.""")
        c = ''
        while not c:
            try:
                c = anything('What would you like your bot\'s prefix '
                             'character(s) to be?')
                conf.squidbot.reply.whenAddressedBy.chars.set(c)
            except registry.InvalidRegistryValue as e:
                output(str(e))
                c = ''
    else:
        conf.squidbot.reply.whenAddressedBy.chars.set('')

    ###
    # logging variables.
    ###

    if advanced:
        # conf.squidbot.log.stdout
        output("""By default, your bot will log not only to files in the logs
        directory you gave it, but also to stdout.  We find this useful for
        debugging, and also just for the pretty output (it's colored!)""")
        stdout = not yn('Would you like to turn off this logging to stdout?',
                        default=False)
        conf.squidbot.log.stdout.setValue(stdout)
        if conf.squidbot.log.stdout():
            # conf.something
            output("""Some terminals may not be able to display the pretty
            colors logged to stderr.  By default, though, we turn the colors
            off for Windows machines and leave it on for *nix machines.""")
            if os.name is not 'nt':
                conf.squidbot.log.stdout.colorized.setValue(
                    not yn('Would you like to turn this colorization off?',
                    default=False))

        # conf.squidbot.log.level
        output("""Your bot can handle debug messages at several priorities,
        CRITICAL, ERROR, WARNING, INFO, and DEBUG, in decreasing order of
        priority. By default, your bot will log all of these priorities except
        DEBUG.  You can, however, specify that it only log messages above a
        certain priority level.""")
        priority = str(conf.squidbot.log.level)
        logLevel = something('What would you like the minimum priority to be?'
                             '  Just press enter to accept the default.',
                             default=priority).lower()
        while logLevel not in ['debug','info','warning','error','critical']:
            output("""That's not a valid priority.  Valid priorities include
            'DEBUG', 'INFO', 'WARNING', 'ERROR', and 'CRITICAL'""")
            logLevel = something('What would you like the minimum priority to '
                                 'be?  Just press enter to accept the default.',
                                 default=priority).lower()
        conf.squidbot.log.level.set(logLevel)

        # conf.squidbot.databases.plugins.serverSpecific

        output("""Many plugins in Squidbot are server-specific.  Their
        databases, likewise, are specific to each server the bot is in.  Many
        people don't want this, so we have one central location in which to
        say that you would prefer all databases for all servers to be shared.
        This variable, squid.databases.plugins.serverSpecific, is that
        place.""")

        conf.squidbot.databases.plugins.serverSpecific.setValue(
            not yn('Would you like plugin databases to be shared by all '
                   'servers, rather than specific to each server the '
                   'bot is in?'))

    output("""There are a lot of options we didn't ask you about simply
              because we'd rather you get up and running and have time
              left to play around with your bot.  But come back and see
              us!  When you've played around with your bot enough to
              know what you like, what you don't like, what you'd like
              to change, then take a look at your configuration file
              when your bot isn't running and read the comments,
              tweaking values to your heart's desire.""")

    # Let's make sure that src/ plugins are loaded.
    conf.registerPlugin('Admin', True)
    conf.registerPlugin('AutoMode', True)
    conf.registerPlugin('Channel', True)
    conf.registerPlugin('Config', True)
    conf.registerPlugin('Misc', True)
    conf.registerPlugin('NickAuth', True)
    conf.registerPlugin('User', True)
    conf.registerPlugin('Utilities', True)

    ###
    # Write the registry
    ###

    # We're going to need to do a darcs predist thing here.
    #conf.squidbot.debug.generated.setValue('...')

    filename = something("""In which file would you like to save
                         this config?""", default='%s.conf' % nick)
    if not filename.endswith('.conf'):
        filename += '.conf'
    registry.close(conf.squidbot, os.path.expanduser(filename))

    # Done!
    output("""All done!  Your new bot configuration is %s.  If you're running
    a *nix based OS, you can probably start your bot with the command line
    "squid %s".  If you're not running a *nix or similar machine, you'll
    just have to start it like you start all your other Python scripts.""" % \
                                                         (filename, filename))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        # We may still be using bold text when exiting during a prompt
        if questions.useBold:
            import squid.ansi as ansi
            print(ansi.RESET)
        print()
        print()
        output("""Well, it looks like you canceled out of the wizard before
        it was done.  Unfortunately, I didn't get to write anything to file.
        Please run the wizard again to completion.""")

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79: