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

"""
Module for general worldly stuff, like global variables and whatnot.
"""

import gc
import os
import sys
import time
import atexit
import select

import re

from . import conf, log, registry
from .utils import minisix

startedAt = time.time() # Just in case it doesn't get set later.

starting = False

commandsProcessed = 0

def _flushUserData():
    userdataFilename = os.path.join(conf.squidbot.directories.conf(),
                                    'userdata.conf')
    registry.close(conf.users, userdataFilename)

flushers = [_flushUserData] # A periodic function will flush all these.

registryFilename = None

def flush():
    """Flushes all the registered flushers."""
    for (i, f) in enumerate(flushers):
        try:
            f()
        except Exception:
            log.exception('Uncaught exception in flusher #%s (%s):', i, f)

def debugFlush(s=''):
    if conf.squidbot.debug.flushVeryOften():
        if s:
            log.debug(s)
        flush()

def upkeep():
    """Does upkeep (like flushing, garbage collection, etc.)"""
    # Just in case, let's clear the exception info.
    try:
        sys.exc_clear()
    except AttributeError:
        # Python 3 does not have sys.exc_clear. The except statement clears
        # the info itself (and we've just entered an except statement)
        pass
    if os.name == 'nt':
        try:
            import msvcrt
            msvcrt.heapmin()
        except ImportError:
            pass
        except IOError: # Win98
            pass
    doFlush = conf.squidbot.flush() and not starting
    if doFlush:
        flush()
        # This is so registry._cache gets filled.
        # This seems dumb, so we'll try not doing it anymore.
        #if registryFilename is not None:
        #    registry.open(registryFilename)
    if not dying:
        #timestamp = log.timestamp()
        if doFlush:
            log.info('Flushers flushed and garbage collected.')
        else:
            log.info('Garbage collected.')
    collected = gc.collect()
    if gc.garbage:
        log.warning('Noncollectable garbage (file this as a bug on SF.net): %s',
                    gc.garbage)
    return collected

def startDying():
    """Starts dying."""
    log.info('Shutdown initiated.')
    global dying
    dying = True

def finished():
    log.info('Shutdown complete.')

# These are in order; don't reorder them for cosmetic purposes.  The order
# in which they're registered is the reverse order in which they will run.
atexit.register(finished)
atexit.register(upkeep)
atexit.register(startDying)

##################################################
##################################################
##################################################
## Don't even *think* about messing with these. ##
##################################################
##################################################
##################################################
dying = False
testing = False
starting = False
profiling = False
documenting = False


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79: