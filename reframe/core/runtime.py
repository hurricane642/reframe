# Copyright 2016-2020 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

#
# Handling of the current host context
#

import os
import functools
import re
import socket
from datetime import datetime

import reframe.core.config as config
import reframe.core.fields as fields
import reframe.utility.os_ext as os_ext
from reframe.core.environments import (Environment, snapshot)
from reframe.core.exceptions import ReframeFatalError
from reframe.core.systems import System


class RuntimeContext:
    '''The runtime context of the framework.

    This class essentially groups the current host system and the associated
    resources of the framework on the current system.
    It also encapsulates other runtime parameters that are relevant to the
    framework's execution.

    There is a single instance of this class globally in the framework.

    .. note::
       .. versionadded:: 2.13

    '''

    def __init__(self, site_config):
        self._site_config = site_config
        self._system = System.create(site_config)
        self._current_run = 0
        self._timestamp = datetime.now()

    def _makedir(self, *dirs, wipeout=False):
        ret = os.path.join(*dirs)
        if wipeout:
            os_ext.rmtree(ret, ignore_errors=True)

        os.makedirs(ret, exist_ok=True)
        return ret

    def _format_dirs(self, *dirs):
        try:
            last = dirs[-1]
        except IndexError:
            return dirs

        current_run = runtime().current_run
        if current_run == 0:
            return dirs

        last += '_retry%s' % current_run
        return (*dirs[:-1], last)

    def next_run(self):
        self._current_run += 1

    @property
    def current_run(self):
        return self._current_run

    @property
    def site_config(self):
        return self._site_config

    @property
    def system(self):
        '''The current host system.

        :type: :class:`reframe.core.runtime.HostSystem`
        '''
        return self._system

    @property
    def prefix(self):
        return os_ext.expandvars(
            self.site_config.get('systems/0/prefix')
        )

    @property
    def stagedir(self):
        return os_ext.expandvars(
            self.site_config.get('systems/0/stagedir')
        )

    @property
    def outputdir(self):
        return os_ext.expandvars(
            self.site_config.get('systems/0/outputdir')
        )

    @property
    def perflogdir(self):
        return os_ext.expandvars(
            self.site_config.get('systems/0/perflogdir')
        )

    @property
    def timestamp(self):
        timefmt = self.site_config.get('general/0/timestamp')
        return self._timestamp.strftime(timefmt)

    @property
    def output_prefix(self):
        '''The output prefix directory of ReFrame.'''
        if self.outputdir:
            return os.path.join(self.outputdir, self.timestamp)
        else:
            return os.path.join(self.prefix, 'output', self.timestamp)

    @property
    def stage_prefix(self):
        '''The stage prefix directory of ReFrame.'''
        if self.stagedir:
            return os.path.join(self.stagedir, self.timestamp)
        else:
            return os.path.join(self.prefix, 'stage', self.timestamp)

    @property
    def perflog_prefix(self):
        if self.perflogdir:
            return self.perflogdir
        else:
            return os.path.join(self.prefix, 'perflogs')

    def make_stagedir(self, *dirs, wipeout=True):
        return self._makedir(self.stage_prefix,
                             *self._format_dirs(*dirs), wipeout=wipeout)

    def make_outputdir(self, *dirs, wipeout=True):
        return self._makedir(self.output_prefix,
                             *self._format_dirs(*dirs), wipeout=wipeout)

    @property
    def modules_system(self):
        '''The modules system used by the current host system.

        :type: :class:`reframe.core.modules.ModulesSystem`.
        '''
        return self._system.modules_system

    def get_option(self, option):
        return self._site_config.get(option)

    def show_config(self):
        '''Return a textual representation of the current runtime.'''
        return str(self._system)


# Global resources for the current host
_runtime_context = None


def init_runtime(site_config):
    global _runtime_context

    if _runtime_context is None:
        _runtime_context = RuntimeContext(site_config)


def runtime():
    '''Retrieve the framework's runtime context.

    :type: :class:`reframe.core.runtime.RuntimeContext`

    .. note::
       .. versionadded:: 2.13
    '''
    if _runtime_context is None:
        raise ReframeFatalError('no runtime context is configured')

    return _runtime_context


def loadenv(*environs):
    '''Load environments in the current Python context.

    Returns a tuple containing a snapshot of the environment at entry to this
    function and a list of shell commands required to load ``environs``.
    '''
    modules_system = runtime().modules_system
    env_snapshot = snapshot()
    commands = []
    for env in environs:
        for m in env.modules:
            conflicted = modules_system.load_module(m, force=True)
            for c in conflicted:
                commands += modules_system.emit_unload_commands(c)

            commands += modules_system.emit_load_commands(m)

        for k, v in env.variables.items():
            os.environ[k] = os_ext.expandvars(v)
            commands.append('export %s=%s' % (k, v))

    return env_snapshot, commands


def emit_loadenv_commands(*environs):
    env_snapshot, commands = loadenv(*environs)
    env_snapshot.restore()
    return commands


def is_env_loaded(environ):
    ''':class:`True` if this environment is loaded, :class:`False` otherwise.
    '''
    is_module_loaded = runtime().modules_system.is_module_loaded
    return (all(map(is_module_loaded, environ.modules)) and
            all(os.environ.get(k, None) == os_ext.expandvars(v)
                for k, v in environ.variables.items()))


class temp_environment:
    '''Context manager to temporarily change the environment.'''

    def __init__(self, modules=[], variables=[]):
        self._modules = modules
        self._variables = variables

    def __enter__(self):
        new_env = Environment('_rfm_temp_env', self._modules, self._variables)
        self._environ_save, _ = loadenv(new_env)
        return new_env

    def __exit__(self, exc_type, exc_value, traceback):
        self._environ_save.restore()


# The following utilities are useful only for the unit tests

class temp_runtime:
    '''Context manager to temporarily switch to another runtime.'''

    def __init__(self, config_file, sysname=None, options=None):
        global _runtime_context

        options = options or {}
        self._runtime_save = _runtime_context
        if config_file is None:
            _runtime_context = None
        else:
            site_config = config.load_config(config_file)
            site_config.select_subconfig(sysname)
            for opt, value in options.items():
                site_config.add_sticky_option(opt, value)

            _runtime_context = RuntimeContext(site_config)

    def __enter__(self):
        return _runtime_context

    def __exit__(self, exc_type, exc_value, traceback):
        global _runtime_context
        _runtime_context = self._runtime_save


def switch_runtime(config_file, sysname=None, options=None):
    '''Function decorator for temporarily changing the runtime for a
    function.'''
    def _runtime_deco(fn):
        @functools.wraps(fn)
        def _fn(*args, **kwargs):
            with temp_runtime(config_file, sysname, options):
                ret = fn(*args, **kwargs)

            return ret

        return _fn

    return _runtime_deco


class module_use:
    '''Context manager for temporarily modifying the module path'''

    def __init__(self, *paths):
        self._paths = paths

    def __enter__(self):
        runtime().modules_system.searchpath_add(*self._paths)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        runtime().modules_system.searchpath_remove(*self._paths)
