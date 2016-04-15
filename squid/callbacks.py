# -*- coding: utf8 -*-
###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2014, James McCoy
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

"""
This module contains the basic callbacks for handling PRIVMSGs.
"""

import re
import copy
import time
from . import shlex
import codecs
import getopt
import inspect

from . import conf, log, registry, utils
from .utils import minisix
from .utils.iter import any, all
from .i18n import PluginInternationalization
_ = PluginInternationalization()

def canonicalName(command, preserve_spaces=False):
    """Turn a command into its canonical form.

    Currently, this makes everything lowercase and removes all dashes and
    underscores.
    """
    if minisix.PY2 and isinstance(command, unicode):
        command = command.encode('utf-8')
    elif minisix.PY3 and isinstance(command, bytes):
        command = command.decode()
    special = '\t-_'
    if not preserve_spaces:
        special += ' '
    reAppend = ''
    while command and command[-1] in special:
        reAppend = command[-1] + reAppend
        command = command[:-1]
    return ''.join([x for x in command if x not in special]).lower() + reAppend

class CanonicalString(registry.NormalizedString):
    def normalize(self, s):
        return canonicalName(s)

class CanonicalNameSet(utils.NormalizingSet):
    def normalize(self, s):
        return canonicalName(s)

class CanonicalNameDict(utils.InsensitivePreservingDict):
    def key(self, s):
        return canonicalName(s)

class Disabled(registry.SpaceSeparatedListOf):
    sorted = True
    Value = CanonicalString
    List = CanonicalNameSet

conf.registerGlobalValue(conf.squidbot.commands, 'disabled',
    Disabled([], _("""Determines what commands are currently disabled.  Such
    commands will not appear in command lists, etc.  They will appear not even
    to exist.""")))

class DisabledCommands(object):
    def __init__(self):
        self.d = CanonicalNameDict()
        for name in conf.squidbot.commands.disabled():
            if '.' in name:
                (plugin, command) = name.split('.', 1)
                if command in self.d:
                    if self.d[command] is not None:
                        self.d[command].add(plugin)
                else:
                    self.d[command] = CanonicalNameSet([plugin])
            else:
                self.d[name] = None

    def disabled(self, command, plugin=None):
        if command in self.d:
            if self.d[command] is None:
                return True
            elif plugin in self.d[command]:
                return True
        return False

    def add(self, command, plugin=None):
        if plugin is None:
            self.d[command] = None
        else:
            if command in self.d:
                if self.d[command] is not None:
                    self.d[command].add(plugin)
            else:
                self.d[command] = CanonicalNameSet([plugin])

    def remove(self, command, plugin=None):
        if plugin is None:
            del self.d[command]
        else:
            if self.d[command] is not None:
                self.d[command].remove(plugin)

class Plugin(object):
    public = True
    noIgnore = False
    classModule = None
    def __init__(self, bot, *args, **kwargs):
        myName = self.name()
        self.log = log.getPluginLogger(myName)
        super(Plugin, self).__init__(*args,**kwargs)
        # We can't do this because of the specialness that Owner and Misc do.
        # I guess plugin authors will have to get the capitalization right.
        # self.callAfter = map(str.lower, self.callAfter)
        # self.callBefore = map(str.lower, self.callBefore)

    def name(self):
        return self.__class__.__name__

    def canonicalName(self):
        return canonicalName(self.name())

    def registryValue(self, name, server=None, value=True):
        plugin = self.name()
        group = conf.squidbot.plugins.get(plugin)
        names = registry.split(name)
        for name in names:
            group = group.get(name)
        if server is not None:
            if hasattr(server,'id'):
                server = server.id
            if server.isdigit():
                group = group.get(server)
            else:
                self.log.debug('%s: registryValue got server=%r', plugin,
                               server)
        if value:
            return group()
        else:
            return group

    def setRegistryValue(self, name, value, server=None):
        plugin = self.name()
        group = conf.squidbot.plugins.get(plugin)
        names = registry.split(name)
        for name in names:
            group = group.get(name)
        if server is None:
            group.setValue(value)
        else:
            if hasattr(server,'id'):
                server = server.id
            group.get(server).setValue(value)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79: