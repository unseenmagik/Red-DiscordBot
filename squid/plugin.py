###
# Copyright (c) 2002-2005, Jeremiah Fincher
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
import imp
import os.path
import linecache
import re

from . import callbacks, conf, log, registry

installDir = os.path.dirname(sys.modules[__name__].__file__)
_pluginsDir = os.path.join(installDir, 'plugins')

class Deprecated(ImportError):
    pass

def loadPluginModule(name, ignoreDeprecation=False):
    """Loads (and returns) the module for the plugin with the given name."""
    files = []
    pluginDirs = conf.squidbot.directories.plugins()[:]
    pluginDirs.append(_pluginsDir)
    for dir in pluginDirs:
        try:
            files.extend(os.listdir(dir))
        except EnvironmentError: # OSError, IOError superclass.
            log.warning('Invalid plugin directory: %s; removing.', dir)
            conf.squidbot.directories.plugins().remove(dir)
    if name not in files:
        search = lambda x: re.search(r'(?i)^%s$' % (name,), x)
        matched_names = list(filter(search, files))
        if len(matched_names) == 1:
            name = matched_names[0]
        else:
            raise ImportError(name)
    moduleInfo = imp.find_module(name, pluginDirs)
    try:
        module = imp.load_module(name, *moduleInfo)
    except:
        sys.modules.pop(name, None)
        keys = list(sys.modules.keys())
        for key in keys:
            if key.startswith(name + '.'):
                sys.modules.pop(key)
        raise
    if 'deprecated' in module.__dict__ and module.deprecated:
        if ignoreDeprecation:
            log.warning('Deprecated plugin loaded: %s', name)
        else:
            raise Deprecated(format('Attempted to load deprecated plugin %s',
                                     name))
    if module.__name__ in sys.modules:
        sys.modules[module.__name__] = module
    linecache.checkcache()
    return module

def renameCommand(cb, name, newName):
    assert not hasattr(cb, newName), 'Cannot rename over existing attributes.'
    assert newName == callbacks.canonicalName(newName), \
           'newName must already be normalized.'
    if name != newName:
        method = getattr(cb.__class__, name)
        setattr(cb.__class__, newName, method)
        delattr(cb.__class__, name)

def registerRename(plugin, command=None, newName=None):
    g = conf.registerGlobalValue(conf.squidbot.commands.renames, plugin,
            registry.SpaceSeparatedSetOfStrings([], """Determines what commands
            in this plugin are to be renamed."""))
    if command is not None:
        g().add(command)
        v = conf.registerGlobalValue(g, command, registry.String('', ''))
        if newName is not None:
            v.setValue(newName) # In case it was already registered.
        return v
    else:
        return g

def loadPluginClass(bot, plugin, register=None):
    """Loads the plugin Class from the given module into the bot."""
    bot.load_extension(plugin)
    cb = bot.extensions.get(plugin,None)
    public = True
    if hasattr(cb, 'public'):
        public = cb.public
    conf.registerPlugin(plugin, register, public)
    try:
        v = registerRename(plugin)
        renames = conf.squidbot.commands.renames.get(plugin)()
        if renames:
            for command in renames:
                v = registerRename(plugin, command)
                newName = v()
                assert newName
                renameCommand(cb, command, newName)
        else:
            conf.squidbot.commands.renames.unregister(plugin)
    except registry.NonExistentRegistryEntry as e:
        pass # The plugin isn't there.
    return cb

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
