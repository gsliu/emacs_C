"""Handles gdb-like command processing.
(See also pydb.doc for documentation.)
$Id: gdb.py.in,v 1.174 2009/03/31 19:52:58 rockyb Exp $"""
# -*- coding: utf-8 -*-
#   Copyright (C) 2007, 2008, 2009 Rocky Bernstein (rocky@gnu.org)
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
#    02110-1301 USA.

_debugger_name = 'pydb'

# The name of the debugger we are currently going by.
_version = '1.26'

import atexit, inspect, linecache, os, pprint, pydoc, shlex
import bdb, dis, disassemble, re, subcmd, sys, types


import bytecode, pydbcmd, pydbbdb
import signal
import sighandler
from complete import *

## from connection import ConnectionServerFactory, ConnectionClientFactory, ConnectionFailed
from bdb         import BdbQuit
from display     import Display, DisplayNode
from fns         import *
from info        import *
from set         import *
from show        import *

from pydbcmd import Cmd
from pydbbdb import Bdb

from threadinfo import *

class Restart(Exception):
    """Causes a debugger to be restarted for the debugged Python program."""
    pass

class Gdb(Bdb, Cmd, SubcmdInfo, SubcmdSet, SubcmdShow):
    """A debugger class for Python that resembles the gdb (GNU debugger)
    command set.

    Parameter completekey specifies the what to use for command completion.
    pass None if no command completion is desired.

    Parameters stdin and stdout specify where debugger input and output
    are to come from.
    
    Parameter siglist gives a list of signals to intercept and ignore.
    None means the default set. If you want *no* signals, use [].
    """

    def __init__(self, completekey='tab', stdin=None, stdout=None,
                 siglist=None):
        pydbbdb.Bdb.__init__(self)
        pydbcmd.Cmd.__init__(self, completekey, stdin, stdout)

        self._program_sys_argv    = []   # sys.argv after options are stripped
        self._re_linetrace_delay  = re.compile(r'\s*linetrace\s+delay')
        self._wait_for_mainpyfile = False

        # set up signal handling
        self.sigmgr          = sighandler.SignalManager(self,
                                                        ignore_list=siglist)
        self._reset_handler  = None

        self.__init_info()   # Initialize 'info' subcommands
        self.__init_set()    # Initialize 'set' subcommands
        self.__init_show()   # Initialize 'show' subcommands

        self.all_completions = lambda arg, left=True: \
                               all_completions(self, arg, left)
        self.autoeval        = True
        self.basename        = False
        self.connection      = None   # For out-of-process communication
        self.currentbp       = None   # for "info program"
        self.cur_frame       = None   # current stack frame
        self.dbg_pydb        = False  # Debug the debugger?
        self.def_trace       = False  # Show/stop at method create statements?
        self.debug_signal    = None   # The signal used by 'attach'
        self.display         = Display()
        self.fntrace         = False  # Tracing functions/methods
        self.gdb_dialect     = True   # Controls how stack is shown
        self.field_BdbQuit   = False  # does dispatcher field BdbQuit?

        # A list of the commands for which the first argument can be a
        # Python object. This is used by subcommand completions.
        self.first_can_be_obj = [
            "disassemble", "examine", "help", "p", "pp", "pydoc", "x",
            "whatis"
            ]
        
        self.is_in_dbg       = is_in_gdb
        self.lastcmd         = ''     # last debugger command run
        self.linetrace       = False
        self.linetrace_delay = 0
        self.listsize        = 10

        # main_dirname is the directory where the script resides;
        # "import" statments are relative to this location.

        self.main_dirname    = os.curdir
        self.mainpyfile      = ''
        self.maxargstrsize   = 100     # max length to show of parameter string
        self.moduletodebug   = ""
        self.noninteractive  = False   # Controls whether to prompt on
                                       # potentially dangerous commands.
        self.originalpath    = sys.path[:]
        self.orig_stdin      = self.stdin
        self.orig_stdout     = self.stdout
        self.running         = False
        self.search_path     = sys.path  # source name search path
        self.sigcheck        = True
        self.stop_reason     = None    # Why are we in the debugger?
        self._sys_argv       = []      # exec sys.argv, e.g. may include pydb
        self.set_history_length   = None
        self.stepping        = False   # used in thread debugging


        self.target          = 'local' # local connections by default
        self.target_addr     = ''      # target address used by 'attach'
        self.width           = 80      # Assume a printed line is this wide

        # self.break_anywhere, self.set_continue and
        # self.trace_dispatch are changed depending on the value of
        # 'set sigcheck'.  We may "decorate", in the design pattern
        # sense, the routines from bdb, so we need to save them.
        self.break_anywhere_old  = self.break_anywhere
        self.set_continue_old    = self.set_continue
        self.trace_dispatch_old  = self.trace_dispatch

        ## FIXME: for now we'll turn on signal trace dispatching
        self.break_anywhere  = self.break_anywhere_gdb
        self.set_continue    = self.set_continue_gdb
        self.trace_dispatch  = self.trace_dispatch_gdb

        # associates a command list to breakpoint numbers
        self.commands = {}

        # for each bp num, tells if the prompt must be disp. after
        # execing the cmd list
        self.commands_doprompt = {}

        # for each bp num, tells if the stack trace must be disp. after
        # execing the cmd list
        self.commands_silent = {}

        # True while in the process of defining a command list
        self.commands_defining = False

        # The breakpoint number for which we are defining a list
        self.commands_bnum = None #

        # list of all the commands making the program
        # resume execution.

        self.commands_resuming = ['do_continue', 'do_jump',  'do_next',
                                  'do_quit',     'do_return',
                                  'do_step']

        self.do_L = self.info_breakpoints

        # Try to load readline if it exists
        try:
            import readline
            import rlcompleter
            self.readline  = readline
            self.completer = rlcompleter.Completer(sys._getframe().f_locals)
            self.hist_last = 0
            self.hist_save = False
            self.set_history_length = readline.set_history_length
            # Set history length using gdb's rule.
            try:
                history_length = int(os.environ['HISTSIZE'])
            except:
                history_length = 256
            self.set_history_length(history_length)

            # An application like ipython may have its own
            # history set up beforehand, clear that so we don't back up
            # into that. Note that ipython saves and restores its own
            # history.
            if hasattr(readline, "clear_history"):
                readline.clear_history()

            # Read history file and set up to write history file when we
            # exit.
            global _debugger_name
            self.histfile = os.path.join(os.environ["HOME"],
                                         ".%shist" % _debugger_name)
            try:
                readline.read_history_file(self.histfile)
            except IOError:
                pass
            atexit.register(self.write_history_file)
            self.do_complete = self.__do_complete

        except ImportError:
            self.histfile = None
            return
        return

    def break_anywhere_gdb(self, frame):
        """Decorate bdb break_anywhere to consider the sigcheck and
        linetrace flags."""
        if self.sigcheck or self.linetrace or self.fntrace: return True
        return self.break_anywhere(frame)

    ### FIXME: trace_dispatch could be a performance bottleneck. If
    ### so, consider reassigning the routine when don't have any
    ### signals registered.
            
    def trace_dispatch_gdb(self, frame, event, arg):
        """Check to see if the signal handler's we are interested have
        changed. If so we'll intercept them. """
        if (not hasattr(self, 'thread_name') 
            or self.thread_name == 'MainThread'):
            self.sigmgr.check_and_adjust_sighandlers()

        # The below variable will be used to scan down frames to determine
        # if trace_dispatch has been called. We key on the variable
        # name, method name, type of variable and even the value.

        breadcrumb = is_in_gdb_dispatch

        try:
            return self.trace_dispatch_old(frame, event, arg)
        except BdbQuit:
            if self.field_BdbQuit:
                # If we have one thread (and know that this this is the case),
                # then we can use sys.exit(). Otherwise kill is the
                # only way to leave.
                if hasattr(sys, '_current_frames'):
                    if len(sys._current_frames()) == 1:
                        sys.exit()
                if self.noninteractive:
                    arg='unconditionally'
                else:
                    arg=''
                self.do_kill('')
                return False
            else:
                raise BdbQuit

    def __adjust_frame(self, pos, absolute_pos):
        """Adjust stack frame by pos positions. If absolute_pos then
        pos is an absolute number. Otherwise it is a relative number.

        If self.gdb_dialect is True, the 0 position is the newest
        entry and doesn't match Python's indexing. Otherwise it does.

        A negative number indexes from the other end."""
        if not self.curframe:
            self.msg("No stack.")
            return

        # Below we remove any negativity. At the end, pos will be
        # the new value of self.curindex.
        if absolute_pos:
            if self.gdb_dialect:
                if pos >= 0:
                    pos = len(self.stack)-pos-1
                else:
                    pos = -pos-1
            elif pos < 0:
                pos = len(self.stack)+pos
        else:
            pos += self.curindex

        if pos < 0:
            self.errmsg("Adjusting would put us beyond the oldest frame")
            return
        elif pos >= len(self.stack):
            self.errmsg("Adjusting would put us beyond the newest frame")
            return

        self.curindex = pos
        self.curframe = self.stack[self.curindex][0]
        self.print_location()
        self.lineno = None

    def __do_complete(self, arg):
        """Print a list of command names that can start with the
        supplied command prefix. If there is no completion nothing
        is printed."""
        completions = self.all_completions(arg)
        if completions is None: return
        for complete in completions:  self.msg(complete)
        return

    def __init_info(self):
        """Initialize info subcommands. Note: instance variable name
        has to be infocmds ('info' + 'cmds') for subcommand completion
        to work."""
        self.infocmds=subcmd.Subcmd("info", self.help_info.__doc__)
        self.infocmds.add('args',           self.info_args)
        self.infocmds.add('breakpoints',    self.info_breakpoints)
        self.infocmds.add('display',        self.info_display)
        self.infocmds.add('handle',         self.sigmgr.info_signal, 1, False)
        self.infocmds.add('globals',        self.info_globals, 1, False)
        self.infocmds.add('line',           self.info_line)
        self.infocmds.add('locals',         self.info_locals,  1, False)
        self.infocmds.add('program',        self.info_program)
        self.infocmds.add('signal',         self.sigmgr.info_signal, 2, False)
        self.infocmds.add('source',         self.info_source, 2)

        if hasattr(sys, "_current_frames"):
            self.info_threads = lambda arg: info_thread_new(self, arg)
            doc               = info_thread_new.__doc__
        else:
            try:
                import threadframe
                sys._current_frames = threadframe.dict # Make it look like 2.5
                self.info_threads   = lambda arg: info_threadframe(self, arg)
                doc                 = info_threadframe.__doc__
                
            except:
                self.info_threads = lambda arg: info_thread_old(self, arg)
                doc               = info_thread_old.__doc__
        self.info_threads.__doc__ = doc

        self.infocmds.add('threads', self.info_threads, 2)
        ## self.infocmds.add('target',         self.info_target)
        return

    def __init_set(self):
        """Initialize set subcommands. Note: instance variable name
        has to be setcmds ('set' + 'cmds') for subcommand completion
        to work."""

        self.setcmds=subcmd.Subcmd("set",   self.help_set.__doc__)
        self.setcmds.add('annotate',        self.set_annotate, 2)
        self.setcmds.add('args',            self.set_args, 2)
        self.setcmds.add('autoeval',        self.set_autoeval, 2)
        self.setcmds.add('basename',        self.set_basename)
        self.setcmds.add('debug-pydb',      self.set_dbg_pydb, 2)
        self.setcmds.add('deftrace',        self.set_deftrace, 2)
        self.setcmds.add('flush',           self.set_flush)
        self.setcmds.add('fntrace',         self.set_fntrace, 2)
        ## self.setcmds.add('debug-signal',    self.set_debug_signal)
        self.setcmds.add('history',         self.set_history)
        self.setcmds.add('interactive',     self.set_interactive)
        self.setcmds.add('linetrace',       self.set_linetrace, 3)
        self.setcmds.add('listsize',        self.set_listsize,  3)
        self.setcmds.add('logging',         self.set_logging,   2)
        self.setcmds.add('maxargsize',      self.set_maxargsize, 2)
        self.setcmds.add('prompt',          self.set_prompt)
        self.setcmds.add('sigcheck',        self.set_sigcheck)
        ## self.setcmds.add('target-address',  self.set_target_address)
        self.setcmds.add('trace-commands',  self.set_cmdtrace)
        self.setcmds.add('warnoptions',     self.set_warnoptions, 2)
        self.setcmds.add('width',           self.set_width,  2)
        return

    def __init_show(self):
        """Initialize show subcommands. Note: instance variable name
        has to be setcmds ('set' + 'cmds') for subcommand completion
        to work."""
        self.showcmds=subcmd.Subcmd("show", self.help_show.__doc__)
        self.showcmds.add('args',           self.show_args)
        self.showcmds.add('annotate',       self.show_annotate, 2)
        self.showcmds.add('autoeval',       self.show_autoeval, 2)
        self.showcmds.add('basename',       self.show_basename)
        self.showcmds.add('debug-pydb',     self.show_dbg_pydb)
        ## self.showcmds.add('debug-signal',   self.show_debug_signal)
        self.showcmds.add('deftrace',       self.show_deftrace,    3)
        self.showcmds.add('commands',       self.show_commands,    2, False)
        self.showcmds.add('directories',    self.show_directories, 1)
        self.showcmds.add('fntrace',        self.show_fntrace,     2)
        self.showcmds.add('flush',          self.show_flush)
        self.showcmds.add('history',        self.show_history)
        self.showcmds.add('interactive',    self.show_interactive)
        self.showcmds.add('linetrace',      self.show_linetrace,   3)
        self.showcmds.add('listsize',       self.show_listsize,    3)
        self.showcmds.add('logging',        self.show_logging,     2)
        self.showcmds.add('maxargsize',     self.show_maxargsize,  2)
        self.showcmds.add('prompt',         self.show_prompt)
        self.showcmds.add('sigcheck',       self.show_sigcheck)
        ## self.showcmds.add('target-address', self.show_target_address)
        self.showcmds.add('trace-commands', self.show_cmdtrace,    1)
        self.showcmds.add('version',        self.show_version)
        self.showcmds.add('warnoptions',    self.show_warnoptions, 2)
        self.showcmds.add('width',          self.show_width, 2)

    # To be overridden in derived debuggers
    def defaultFile(self):
        """Produce a reasonable default."""
        filename = self.curframe.f_code.co_filename
        # Consider using is_exec_stmt(). I just don't understand
        # the conditions under which the below test is true.
        if filename == '<string>' and self.mainpyfile:
            filename = self.mainpyfile
        return filename

    def display_enable(self, arg, flag):
        # arg is list of display points
        for i in arg:
            i = self.get_an_int(i, 'index %r is not a number' % i)
            if i is not None:
                self.display.enable_disable(i, flag)
                pass
            pass
        return

    def lineinfo(self, identifier):
        failed = (None, None, None)
        # Input is identifier, may be in single quotes
        idstring = identifier.split("'")
        if len(idstring) == 1:
            # not in single quotes
            ident = idstring[0].strip()
        elif len(idstring) == 3:
            # quoted
            ident = idstring[1].strip()
        else:
            return failed
        if ident == '': return failed
        parts = ident.split('.')
        # Protection for derived debuggers
        if parts[0] == 'self':
            del parts[0]
            if len(parts) == 0:
                return failed
        # Best first guess at file to look at
        fname = self.defaultFile()
        if len(parts) == 1:
            item = parts[0]
        else:
            # More than one part.
            # First is module, second is method/class
            f = self.lookupmodule(parts[0])
            if f:
                fname = f
            item = parts[1]
        answer = find_function(item, fname)
        return answer or failed

    def forget(self):
        self.lineno = None
        self.stack = []
        self.curindex = 0
        self.curframe = None
        return

    def interaction(self, frame, tb):
        """Possibly goes into loop to read debugger commands."""
        do_loop = self.setup(frame, tb) != 1
        if do_loop:
            if frame or tb:
                self.print_location(print_line=self.linetrace or self.fntrace)
                self.display.display(self.curframe)
            if not self.noninteractive:
                try:
                    self.cmdloop()
                except KeyboardInterrupt:
                    self.do_quit(None)
        self.currentbp = None    # Can forget it now that we're moving on
        self.forget()
        if not do_loop:
            # Tell cmdloop to break out of its loop.
            return True
        return False

    def parse_list_cmd(self, arg):
        """Parses arguments for the "list" command and returns the tuple
        filename, start, last
        or sets these to None if there was some problem."""

        if not self.curframe:
            self.msg("No Python program loaded.")
            return (None, None, None)

        self.lastcmd = 'list'
        last = None
        filename = self.curframe.f_code.co_filename
        if arg:
            if arg == '-':
                first = max(1, self.lineno - 2*self.listsize - 1)
            elif arg == '.':
                first = max(1, 
                            inspect.getlineno(self.curframe) - self.listsize/2)
            else:
                args = arg.split()
                (modfunc, filename, first) = parse_filepos(self, args[0])
                if first == None and modfunc == None:
                    # error should have been shown previously
                    return (None, None, None)
                if len(args) == 1:
                    first = max(1, first - (self.listsize/2))
                elif len(args) == 2:
                    (modfunc, last_filename, last) = \
                               parse_filepos(self, args[1])
                    if filename != last_filename \
                       and filename is not None and last_filename is not None:
                        self.errmsg('filename in the range must be the same')
                        return (None, None, None)
                    if last < first:
                        i = self.get_an_int(args[1],
                                            ('2nd number (%s) is less than the'
                                            + ' 1st number %d, but it does not'
                                            + ' evaluate to an integer')
                                            % (args[1], first))
                        if i is None:
                            return (None, None, None)
                        # Assume last is a count rather than an end line number
                        last = first + last
                elif len(args) > 2:
                    self.errmsg('At most 2 arguments allowed. Saw: %d' %
                                len(args))
                    return (None, None, None)
        elif self.lineno is None or not self.running:
            first = max(1, inspect.getlineno(self.curframe) - self.listsize/2)
        else:
            first = self.lineno + 1
        if last is None:
            last = first + self.listsize - 1

        return (filename, first, last)

    def set_continue_gdb(self):
        """Like bdb's set_continue but we don't have the run fast
        option"""
        self.stopframe = self.botframe
        self.returnframe = None
        self.quitting = 0
        return

    def setup(self, frame, tb=None):
        """Initialization done before entering the debugger-command
        loop. In particular we set up the call stack used for local
        variable lookup and frame/up/down commands.

        We return True if we should NOT enter the debugger-command
        loop."""
        self.forget()
        if self.dbg_pydb:
            frame = inspect.currentframe()
        if frame or tb:
            self.stack, self.curindex = self.get_stack(frame, tb)
            self.curframe = self.stack[self.curindex][0]
        else:
            self.stack = self.curframe = self.botframe = None
        if self.execRcLines()==1: return True
        return False

    def setup_source(self, arg, showError=False):
        """Set up to read commands from a source file"""
        try:
            rcFile = open(os.path.join(arg))
        except IOError, (errno, strerror):
            if showError:
                self.errmsg("Error opening debugger command file %s: %s"
                            % (arg, strerror))
            pass
        else:
            for line in rcFile.readlines():
                self.rcLines.append(line)
            rcFile.close()
        return

    def show_commands(self, arg):
        """Show the history of commands you typed.
You can supply a command number to start with, or a `+' to start after
the previous command number shown. A negative number starts from the end."""
        try:
            import readline
            if self.histfile is not None:
                hist_max = readline.get_current_history_length()
                if len(arg) <= 1:
                    first=1
                    self.hist_last=hist_max
                else:
                    if arg[1] == '+':
                        first = self.hist_last+1
                        self.hist_last = min(hist_max,
                                             first + self.listsize)
                    else:
                        try:
                            center = self.get_int(arg[1],
                                                  cmdname="show commands")
                        except ValueError:
                            return
                        if center < 0: center = hist_max + center + 1
                        first = max(1, center - (self.listsize/2))
                        self.hist_last = min(hist_max,
                                             center + (self.listsize/2))
                i=first
                while i<=self.hist_last:
                    self.msg("%5d  %s" % (i, readline.get_history_item(i)))
                    i += 1
            else:
                self.errmsg("History mechanism turned off.")
        except ImportError:
            self.errmsg("Readline not available.")

    def show_history(self, args):
        """Generic command for showing command history parameters"""
        try:
            import readline
            if len(args) > 1 and args[1]:
                show_save = show_size = show_filename = False
                show_prefix = False
                if args[1] == 'filename':
                    show_filename = True
                elif args[1] == 'save':
                    show_save = True
                elif args[1] == 'size':
                    show_size = True
                else:
                    self.undefined_cmd("show history", args[1])
                    return
            else:
                show_save = show_size = show_filename = True
                show_prefix = True
            if show_filename:
                if show_prefix:
                    prefix='filename: '
                else:
                    prefix=''
                self.msg("""%sThe filename in which to record the command history is
"%s".""" % (prefix, self.histfile))
            if show_save:
                if show_prefix:
                    prefix='save: '
                else:
                    prefix=''
                self.msg("%sSaving of the history record on exit is %s"
                         % (prefix, show_onoff(self.hist_save)))
            if show_size:
                if show_prefix:
                    prefix='size: '
                else:
                    prefix=''
                self.msg("%sThe size of the command history is %d"
                         % (prefix, readline.get_history_length()))
        except ImportError:
            pass

    def show_listsize(self, args):
        "Show number of source lines the debugger will list by default"
        self.msg("Number of source lines %s will list by default is %d." \
                 % (_debugger_name, self.listsize))

    def show_prompt(self, args):
        "Show debugger's prompt"
        self.msg("""%s's prompt is "%s".""" %
                 (_debugger_name, self.prompt))
        return

    def show_version(self, args):
        """Show what version of the debugger this is"""
        global _version
        self.msg("""%s version %s.""" %
                 (_debugger_name, _version))
        return

    def write_history_file(self):
        """Write the command history file -- possibly."""
        if self.hist_save:
            try:
                import readline
                try:
                    readline.write_history_file(self.histfile)
                except IOError:
                    pass
            except ImportError:
                pass

    ###################################################################
    # Command definitions, called by cmdloop()
    # The argument is the remaining string on the command line
    # Return true to exit from the command loop
    ###################################################################

    def do_alias(self, arg):
        """alias [name [command [parameter parameter ...] ]]
Creates an alias called 'name' the executes 'command'.  The command
must *not* be enclosed in quotes.  Replaceable parameters are
indicated by %1, %2, and so on, while %* is replaced by all the
parameters.  If no command is given, the current alias for name
is shown. If no name is given, all aliases are listed.

Aliases may be nested and can contain anything that can be
legally typed at the debugger prompt.  Note!  You *can* override
internal debugger commands with aliases!  Those internal commands
are then hidden until the alias is removed.  Aliasing is recursively
applied to the first word of the command line; all other words
in the line are left alone.

Some useful aliases (especially when placed in the .pydbsrc file) are:

#Print instance variables (usage "pi classInst")
alias pi for k in %1.__dict__.keys(): print "%1.",k,"=",%1.__dict__[k]

#Print instance variables in self
alias ps pi self
"""
        args = arg.split()
        if len(args) == 0:
            keys = self.aliases.keys()
            keys.sort()
            for alias in keys:
                self.msg("%s = %s" % (alias, self.aliases[alias]))
            return
        if args[0] in self.aliases and len(args) == 1:
            self.msg("%s = %s" % (args[0], self.aliases[args[0]]))
        else:
            self.aliases[args[0]] = ' '.join(args[1:])

    def do_break(self, arg, temporary = 0, thread_name=None):

        """b(reak) [[file:]lineno | function] [, condition]

With a line number argument, set a break there in the current file.
With a function name, set a break at first executable line of that
function.  Without argument, set a breakpoint at current location.  If
a second argument is present, it is a string specifying an expression
which must evaluate to true before the breakpoint is honored.

The line number may be prefixed with a filename and a colon,
to specify a breakpoint in another file (probably one that
hasn't been loaded yet).  The file is searched for on sys.path;
the .py suffix may be omitted."""
        if not self.curframe:
            self.msg("No stack.")
            return
        cond = None
        funcname = None
        if not arg:
            if self.lineno is None:
                lineno = max(1, inspect.getlineno(self.curframe))
            else:
                lineno = self.lineno + 1
            filename = self.curframe.f_code.co_filename
        else:
            # parse arguments; comma has lowest precedence
            # and cannot occur in filename
            filename = None
            lineno = None
            comma = arg.find(',')
            if comma > 0:
                # parse stuff after comma: "condition"
                cond = arg[comma+1:].lstrip()
                arg = arg[:comma].rstrip()
            (funcname, filename, lineno) = parse_filepos(self, arg)
            if lineno is None: return

        # FIXME This default setting doesn't match that used in
        # do_clear. Perhaps one is non-optimial.
        if not filename:
            filename = self.defaultFile()

        # Check for reasonable breakpoint
        line = checkline(self, filename, lineno)
        if line:
            # now set the break point
            # Python 2.3.5 takes 5 args rather than 6.
            # There is another way in configure to test for the version,
            # but this works too.
            try:
               err = self.set_break(filename, line, temporary, cond, funcname)
            except TypeError:
               err = self.set_break(filename, line, temporary, cond)

            if err: self.errmsg(err)
            else:
                bp = self.get_breaks(filename, line)[-1]
                if thread_name is None:
                    self.msg("Breakpoint %d set in file %s, line %d."
                             % (bp.number, self.filename(bp.file), bp.line))
                else:
                    bp.thread_name = thread_name
                    self.msg("Breakpoint %d set in file %s, line %d, thread %s."
                             % (bp.number, self.filename(bp.file), bp.line,
                                thread_name))

    do_b = do_break

    def do_cd(self, arg):
        """Set working directory to DIRECTORY for debugger and program
        being debugged. """
        if not arg:
            self.errmsg("Argument required (new working directory).")
        else:
            os.chdir(arg)
            return
        return

    def do_clear(self, arg):
        """cl(ear) {[file:]linenumber | function}

        Clear breakpoint at specified line or function.  Argument may
        be line number, function name, or '*' and an address.  If line
        number is specified, all breakpoints in that line are cleared.
        If function is specified, breakpoints at beginning of function
        are cleared.  If an address is specified, breakpoints at that
        address are cleared.

        With no argument, clears all breakpoints in the line that the
        selected frame is executing in.

        See also the 'delete' command which clears breakpoints by number.
        """

        if not self.curframe:
            self.msg("No frame selected.")
            return False
        if not arg:
            frame, lineno = self.stack[self.curindex]
            filename = self.canonic_filename(self.curframe)

        else:
            if ':' in arg:
                # Make sure it works for "clear C:\foo\bar.py:12"
                i = arg.rfind(':')
                filename = arg[:i]
                arg = arg[i+1:]
                try:
                    lineno = int(arg)
                except:
                    self.errmsg("Invalid line number (%s)" % arg)
                    return False
            else:
                (funcname, filename, lineno) = get_brkpt_lineno(self, arg)

            if lineno is None: return False

            # FIXME This default setting doesn't match that used in
            # do_break. Perhaps one is non-optimial.
            if filename is None:
                filename = self.canonic_filename(self.curframe)

        brkpts = self.clear_break(filename, lineno)

        if len(brkpts) > 0:
            if len(brkpts) == 1:
                self.msg("Deleted breakpoint %d" % brkpts[0])
            else:
                self.msg("Deleted breakpoints " +
                         ' '.join(map(lambda b: str(b), brkpts)))
                return False
            return False
        return False

    do_cl = do_clear

    def do_commands(self, arg):

        """Defines a list of commands associated to a breakpoint Those
        commands will be executed whenever the breakpoint causes the
        program to stop execution."""

        if not arg:
            bnum = len(bdb.Breakpoint.bpbynumber)-1
        else:
            try:
                bnum = self.get_pos_int(arg, min_value=0, default=None,
                                        cmdname="'commands'")
            except ValueError:
                return False
        if not (bnum < len(bdb.Breakpoint.bpbynumber)):
            self.errmsg('No breakpoint numbered %d.' % bnum)
            return False

        self.commands_bnum = bnum
        self.commands[bnum] = []
        self.commands_doprompt[bnum] = True
        self.commands_silent[bnum] = False

        self.commands_defining = True
        if self.setup(self.curframe) == 1:
            self.commands_defining = False
            return False

        prompt_back = self.prompt
        self.prompt = '>'
        self.msg("Type commands for when breakpoint %d is hit, one per line."
                 % bnum)
        self.msg('End with a line saying just "end".')

        self.cmdloop()
        self.commands_defining = False
        self.prompt = prompt_back
        return False

    def do_condition(self, arg):
        """condition bpnumber str_condition

        str_condition is a string specifying an expression which must
        evaluate to true before the breakpoint is honored.  If
        str_condition is absent, any existing condition is removed;
        i.e., the breakpoint is made unconditional."""

        args = arg.split(' ', 1)
        try:
            bpnum = self.get_pos_int(args[0].strip(), min_value=1,
                                     cmdname='condition')
        except ValueError:
            return
        except IndexError:
            self.errmsg("Breakpoint number required.")
        try:
            cond = args[1]
        except:
            cond = None
        try:
            bp = bdb.Breakpoint.bpbynumber[bpnum]
        except IndexError:
            self.errmsg("No breakpoint numbered %d." % bpnum)
            return False
        if bp:
            bp.cond = cond
            if not cond:
                self.msg('Breakpoint %d is now unconditional.' % bpnum)

    # Note: ddd only uses first line of docstring after the command name.
    # That is the part that starts Continue execution...
    # So make sure this is a complete sentence.
    def do_continue(self, arg):
        """c(ontinue) [[file:]lineno | function]

Continue execution; only stop when a breakpoint is encountered. If a
line position is given, continue until that line is reached. This is
exactly the same thing as setting a temporary breakpoint at that
position before running an (unconditional) continue."""
        if not self.is_running(): return
        if self.linetrace or self.fntrace:
            # linetracing is like stepping, but we just don't stop. If
            # we were to calling set_continue, it  *might* remove all
            # stopping if there were no breakpoints.
            self.step_ignore = -1
            self.set_step()
            self.stepping = True
        else:
            self.stepping = False

        if arg:
            (funcname, filename, lineno) = parse_filepos(self, arg)
            if lineno:
                self.do_tbreak(arg)

        # This has to be done after do_tbreak
        if not (self.linetrace or self.fntrace):
            self.set_continue()
            
        # Tell cmdloop to break out of its loop.
        return True

    do_c = do_continue

    def do_debug(self, arg):
        """debug code
        Enter a recursive debugger that steps through the code argument
        (which is an arbitrary expression or statement to be executed
        in the current environment)."""
        if not self.curframe:
            self.msg("No frame selected.")
            return
        sys.settrace(None)
        global_vars = self.curframe.f_globals
        local_vars = self.curframe.f_locals
        p = Gdb()
        p.prompt  = "(%s) " % self.prompt.strip()
        self.msg("ENTERING RECURSIVE DEBUGGER")

        # Inherit some values from current environemnt
        p.aliases         = self.aliases
        p.basename        = self.basename
        p.cmdtrace        = self.cmdtrace
        p.fntrace         = self.fntrace
        p.gdb_dialect     = self.gdb_dialect
        p.infocmds        = self.infocmds
        p.linetrace       = self.linetrace
        p.linetrace_delay = self.linetrace_delay
        p.listsize        = self.listsize
        p.noninteractive  = self.noninteractive
        for attr in ('thread_name', 'no_thread_do_break', 'nothread_do_tbreak',
                     'nothread_trace_dispatch', 'nothread_quit',
                     'desired_thread'):
            if hasattr(self, attr):
                setattr(p, attr, getattr(self, attr))

        # Some values that are different from the current environment
        # and different from the default initialization values.
        p.running         = True  # We *are* trying to run something
        p.step_ignore     = 1     # We need to skip one statement

        sys.call_tracing(p.run, (arg, global_vars, local_vars))
        self.msg("LEAVING RECURSIVE DEBUGGER")
        # sys.settrace() seems to mess up self.print_location
        # so print location first.
        self.print_location()
        sys.settrace(self.trace_dispatch)
        self.lastcmd = p.lastcmd
        return False

    def do_delete(self, arg):
        """delete [bpnumber [bpnumber...]]  - Delete some breakpoints.
        Arguments are breakpoint numbers with spaces in between.  To
        delete all breakpoints, give no argument.  those breakpoints.
        Without argument, clear all breaks (but first ask
        confirmation).

        See also the 'clear' command which clears breakpoints by
        line/file number.."""
        if not arg:
            if get_confirmation(self, 'Delete all breakpoints'):
                self.clear_all_breaks()
            return

        numberlist = arg.split()
        for arg in numberlist:
            try:
                i = self.get_pos_int(arg, min_value=1, default=None,
                                     cmdname='delete')
            except ValueError:
                continue

            if not (i < len(bdb.Breakpoint.bpbynumber)):
                self.errmsg('No breakpoint numbered %d.' % i)
                continue
            err = self.clear_bpbynumber(i)
            if err:
                self.errmsg(err)
            else:
                self.msg('Deleted breakpoint %d' % i)

    def do_directory(self, arg):

        """Add directory DIR to beginning of search path for source
files.  Forget cached info on source file locations and line
positions.  DIR can also be $cwd for the current working directory, or
$cdir for the directory in which the source file was compiled into
object code.  With no argument, reset the search path to $cdir:$cwd,
the default."""
        args = arg.split()
        if len(args) == 0:
            if get_confirmation(self,
                'Reinitialize source path to empty'):
                self.search_path=[]
            return
        else:
            # FIXME: Loop over arguments checking for directory?
            self.search_path.insert(0, args[0])

    def do_disable(self, arg):
        """disable [display] bpnumber [bpnumber ...]

        Disables the breakpoints given as a space separated list of bp
        numbers."""

        args = arg.split()
        if len(args) == 0:
            self.errmsg('No breakpoint number given.')
            return
        if args[0] == 'display':
            self.display_enable(args[1:], 0)
            return
        for i in args:
            try:
                i = int(i)
            except ValueError:
                self.msg('Breakpoint index %r is not a number.' % i)
                continue

            if not (0 <= i < len(bdb.Breakpoint.bpbynumber)):
                self.msg('No breakpoint numbered %d.' % i)
                continue

            bp = bdb.Breakpoint.bpbynumber[i]
            if bp:
                bp.disable()

    def do_disassemble(self, arg):
        """disassemble [obj-or-class] [[+|-]start-line [[+|-]end-line]]

With no argument, disassemble the current frame.  With a start-line
integer, the disassembly is narrowed to show lines starting at that
line number or later; with an end-line number, disassembly stops
when the next line would be greater than that or the end of the code
is hit. If start-line or end-line has a plus or minus prefix, then the
line number is relative to the current frame number.

With a class, method, function, code or string argument disassemble
that."""

        if arg:
            args = arg.split()
        else:
            args = []
        start_line = end_line = None
        relative_pos = False
        if len(args) > 0:
            if args[0] in ['+', '-']: 
                start_line = self.curframe.f_lineno
                relative_pos = True
            else:
                start_line = int(args[0])
                if args[0][0:1] in ['+', '-']: 
                    relative_pos = True
                    start_line += self.curframe.f_lineno
                    pass
                pass

            if len(args) == 2:
                try:
                    end_line = self.get_int(args[1], cmdname="disassemble")
                except ValueError:
                    return False
            elif len(args) > 2:
                self.errmsg("Expecting 1-2 line parameters, got %d" %
                            len(args))
                return False
            if not self.curframe:
                self.errmsg("No frame selected.")
                return False
            disassemble.disassemble(self, self.curframe.f_code,
                                    start_line=start_line,
                                    end_line=end_line,
                                    relative_pos=relative_pos)
            pass
        try:
            if len(args) > 1:
                try:
                    start_line = self.get_int(args[1],
                                              cmdname="disassemble")
                    if args[1][0:1] in ['+', '-']: 
                        relative_pos = True
                        start_line += self.curframe.f_lineno
                        pass
                    if len(args) == 3:
                        end_line = self.get_int(args[2],
                                                cmdname="disassemble")
                    elif len(args) > 3:
                        self.errmsg("Expecting 0-3 parameters, got %d" %
                                    len(args))
                        return False
                except ValueError:
                    return False
                pass
            
                if hasattr(self, 'curframe') and self.curframe:
                    obj=self.getval(args[0])
                else:
                    obj=eval(args[0])
                    pass
                disassemble.dis(self, obj,
                                start_line=start_line, end_line=end_line,
                                relative_pos=relative_pos)
        except NameError:
            self.errmsg("Object '%s' is not something we can disassemble"
                        % args[0])
        return False

    def do_display(self, arg):
        """display [format] EXP

        Print value of expression EXP each time the program stops.
        FMT may be used before EXP and may be one of 'c' for char,
        'x' for hex, 'o' for octal, 'f' for float or 's' for string.

        With no argument, display all currently requested auto-display
        expressions.  Use "undisplay" to cancel display requests previously
        made."""

        if not arg:
            # Display anything active
            self.display.display(self.curframe)
        else:
            # Set up a display
            arglist = arg.split()
            if len(arglist) == 2:
               format, variable = arglist
            else:
               format = ""
               variable = arglist[0]
            dp = DisplayNode(self.curframe, variable, format)
            res = dp.checkValid(self.curframe)
            self.msg(res)
        return False

    def do_down(self, arg):
        """d(own) [count]

        Move the current frame one level down in the stack trace
        (to a newer frame).

        If using gdb dialect up matches the gdb: 0 is the most recent
        frame.  Otherwise we match Python's stack: 0 is the oldest
        frame.  """

        try:
            count = self.get_int(arg, cmdname="down")
        except ValueError:
            return
        if self.gdb_dialect:
            count = -count
        self.__adjust_frame(pos=-count, absolute_pos=False)
        return False

    def do_enable(self, arg):
        """enable [display] bpnumber [bpnumber ...]]

        Enables the breakpoints given as a space separated list of bp
        numbers."""
        args = arg.split()
        if len(args) == 0:
            self.errmsg('No breakpoint number given')
            return

        if args[0] == 'display':
            self.display_enable(args[1:], True)
            return

        for i in args:
            i = self.get_an_int(i, 'Breakpoint index %r is not a number' % i)
            if i is None: continue

            if not (1 <= i < len(bdb.Breakpoint.bpbynumber)):
                self.errmsg('No breakpoint numbered %d.' % i)
                continue

            bp = bdb.Breakpoint.bpbynumber[i]
            if bp:
                bp.enable()

    def do_examine(self, arg):
        """examine expression - Print the expression, its value, type,
        and object attributes."""
        s = print_obj(arg, self.curframe)
        self.msg(s)

    do_x = do_examine

    def do_file(self, fname):
        """Use FILE as the Python program to be debugged.
It is compiled and becomes is the program executed when you use the `run'
command.  If no filename is given, this means to set things so there
is no Python file."""
        
        if fname == "":
           if self.mainpyfile == "":
               self.msg('No exec file now.\nNo symbol file now.')
               return
           else:
               # should confirm this per
               if get_confirmation(self, "Discard symbol table from '%s'"
                                   % self.mainpyfile):
                   # XXX how to clean up name space ??
                   self._program_sys_argv = None
                   self.mainpyfile = ''
        else:
            # XXX how to clean up name space ??
            if os.path.exists(fname):
                self.mainpyfile=fname
                self._program_sys_argv = [self.mainpyfile]
                self._runscript(self.mainpyfile)
                # Fake up curframe? 
                return self.quitting
            else:
                self.errmsg("file '%s' does not exist" % fname)
                return None
            pass
        pass

    def do_finish(self, arg):
        """finish

        Continue execution until the current function returns."""
        if not self.is_running(): return
        self.set_return(self.curframe)
        self.stepping = False
        if self.linetrace:
            self.stepping    = True
            self.step_ignore = -1
            self.stopframe   = None

        # Tell cmdloop to break out of its loop.
        return True

    def do_frame(self, arg):
        """frame [frame-number]

        Move the current frame to frame `frame-number' if specified,
        or the current frame, 0 if no frame number specified.

        A negative number indicates position from the other end.
        So 'frame -1' moves when gdb dialect is in effect moves
        to the oldest frame, and 'frame 0' moves to the newest frame."""

        if not self.stack:
            self.msg("Program has no stack frame set.")
            return False
        arg = arg.strip() or '0'
        arg = self.get_an_int(arg,
                              ("The 'frame' command requires a frame number."+
                               " Got: %s") % arg)
        if arg is None: return False

        i_stack = len(self.stack)
        if arg < -i_stack or arg > i_stack-1:
            self.errmsg('Frame number has to be in the range %d to %d' \
                  % (-i_stack, i_stack-1))
        else:
            self.__adjust_frame(pos=arg, absolute_pos=True)
        return False

    def do_handle(self, arg):
        """Specify how to handle a signal.
        
Args are signals and actions to apply to those signals.
recognized actions include "stop", "nostop", "print", "noprint",
"pass", "nopass", "ignore", or "noignore".

- Stop means reenter debugger if this signal happens (implies print and
  nopass).
- Print means print a message if this signal happens.
- Pass means let program see this signal; otherwise program doesn't know.
- Ignore is a synonym for nopass and noignore is a synonym for pass.
- Pass and Stop may not be combined. (This is different from gdb)
        """
        self.sigmgr.action(arg)

    def do_ignore(self,arg):
        """ignore bpnumber count

        Sets the ignore count for the given breakpoint number.  A
        breakpoint becomes active when the ignore count is zero.  When
        non-zero, the count is decremented each time the breakpoint is
        reached and the breakpoint is not disabled and any associated
        condition evaluates to true."""
        args = arg.split()

        bpnum = self.get_an_int(args[0],
                                ("ignore: bpnumber %s does not evaluate to an"
                                + " integer") % args[0], min_value=1)
        if bpnum is None: return False
        if not (0 <= bpnum < len(bdb.Breakpoint.bpbynumber)):
                self.errmsg('No breakpoint numbered %d.' % bpnum)
                return False

        if len(args) > 1:
            count = self.get_an_int(args[1],
                                    ("ignore: count %s does not evaluate to an"
                                    + " integer.") % args[0], min_value=0)
            if count is None: return False
        else:
            count = 0
            
        bp = bdb.Breakpoint.bpbynumber[bpnum]
        if bp:
            bp.ignore = count
            if count > 0:
                reply = 'Will ignore next '
                if count > 1:
                    reply = reply + '%d crossings' % count
                else:
                    reply = reply + '1 crossing'
                self.msg('%s of breakpoint %d.' % (reply, bpnum))
            else:
                self.msg('Will stop next time breakpoint %d is reached.' %
                         bpnum)
            return False
        return False

    def do_ipython(self, arg_str):
        """ipython [ipython-opt1 ipython-opt2 ...]

Run IPython as a command subshell. You need to have ipython installed
for this command to work. If no IPython options are given, the
following options are passed: 
   -noconfirm_exit -prompt_in1 'Pydbgr In [\#]: '

You can access debugger state via local variable "ipydb".
Debugger commands like are installed as IPython magic commands, e.g.
%list, %up, %where.
"""

        if not self.is_running():
            return False

        if arg_str:
            argv = arg_split(arg_str, posix=True)
        else:
            argv = ['-noconfirm_exit','-prompt_in1', 'Pydb In [\\#]: ']
            pass

        if self.curframe and self.curframe.f_locals:
            user_ns = self.curframe.f_locals
        else:
            user_ns = {}

        # IPython does it's own history thing.
        # Make sure it doesn't damage ours.
        if self.readline:
            try:
                self.write_history_file()
            except IOError:
                pass

        # ipython should be around - it was before.
        try:
            import IPython
        except ImportError:
            self.errmsg("IPython doesn't seem to be importable.")
            return False

        user_ns['ipydb'] = self
        ipshell = IPython.Shell.IPShellEmbed(argv=argv, user_ns=user_ns)
        user_ns['ipshell'] = ipshell

        # Give ipython and the user a way to get access to the debugger
        setattr(ipshell, 'ipydb', self)

        if hasattr(ipshell.IP, "magic_pydb"):
            # We get an infinite loop when doing recursive edits
            self.msg("Removing magic %pydb")
            delattr(ipshell.IP, "magic_pydb")
            pass
        
        # add IPython "magic" commands for all debugger comamnds and
        # aliases.  No doubt, this probably could be done in a
        # better way without "exec".  (Someone just needs to suggest
        # a way...)
        ip = IPython.ipapi.get()
        magic_fn_template="""
def ipy_%s(self, args):
   dbg = self.user_ns['ipydb']
   dbg.continue_running = dbg.do_%s(args)
   if dbg.continue_running: self.shell.exit()
   return
ip.expose_magic("%s", ipy_%s)
"""
        expose_magic_template = 'ip.expose_magic("%s", ipy_%s)'
        for name in self.get_cmds():
            exec magic_fn_template % ((name,) * 4)
            pass
            
        # And just when you thought we've forgotten about running
        # the shell...
        ipshell()

        # Restore our history if we can do so.
        if self.readline and self.histfile is not None:
            try:
                self.readline.read_history_file(self.histfile)
            except IOError:
                pass
            return False
        return self.continue_running
                
    def do_info(self, arg):

        """Generic command for showing things about the program being
        debugged. You can give unique prefix of the name of a subcommand to
        get info about just that subcommand."""

        if not arg:
            for subcommand in self.infocmds.list():
                # Some commands have lots of output.
                # they are excluded here because 'in_list' is false.
                if self.infocmds.subcmds[subcommand]['in_list']:
                    self.msg_nocr("%s: " % subcommand)
                    self.do_info(subcommand)
            return

        else:
            args = arg.split()
            self.infocmds.do(self, args[0], args)

    def do_jump(self, arg, cmdname='Jump'):
        """jump lineno

        Set the next line that will be executed."""

        if not self.is_running(): return False

        if self.curindex + 1 != len(self.stack):
            self.errmsg("You can only jump within the bottom frame")
            return False
        arg = self.get_an_int(str(arg),
                              "jump: a line number is required, got %s." %
                              arg)
        if arg is None: return False
        try:
            # Do the jump, fix up our copy of the stack, and display the
            # new position
            self.curframe.f_lineno = arg
            self.stack[self.curindex] = self.stack[self.curindex][0], arg
            self.print_location()
        except ValueError, e:
            self.errmsg('%s failed: %s' % (cmdname, e))
        return False

    def do_kill(self, arg):
        """kill [unconditionally]

Kill execution of program being debugged.

Equivalent of kill -KILL <pid> where <pid> is os.getpid(), the current
debugged process. This is an unmaskable signal. When all else fails, e.g. in
thread code, use this.

If 'unconditionally' is given, no questions are asked. Otherwise, if
we are in interactive mode, we'll prompt to make sure.
"""
        if len(arg) > 0 and 'unconditionally'.startswith(arg) or \
               get_confirmation(self, 'Really do a hard kill', True):
            os.kill(os.getpid(), signal.SIGKILL)
            return False # Possibly not reached
        pass

    def do_list(self, arg):
        """l(ist) [- | . | first [last or count]]

List source code. 

Without arguments, list LISTSIZE lines centered around the current
line or continue the previous listing. "list -" lists LISTSIZE lines
before a previous listing. "list ." means list centered around the current
frame pointer.

With one argument other than "-" or '.', list LISTSIZE lines centered
around the specified position.  With two arguments, list the given
range; if the second argument is less than the first, it is a count.
First and last can be either a function name, a line number or
file:line"""

        filename, first, last = self.parse_list_cmd(arg)
        if filename is None: return
        breaklist = self.get_file_breaks(filename)

        # Python 2.5 or greater has 3 arg getline which handles
        # eggs and zip files
        if 3 == linecache.getline.func_code.co_argcount:
            getline = lambda f, l: linecache.getline(f, l, 
                                                     self.curframe.f_globals)
        else:
            getline = lambda f, l: linecache.getline(f, l)
            pass

        # We now have range information. Do the listing.
        try:
            for lineno in range(first, last+1):
                line = getline(filename, lineno)
                if not line:
                    self.msg('[EOF]')
                    break
                else:
                    s = self._saferepr(lineno).rjust(3)
                    if len(s) < 4: s = s + ' '
                    if lineno in breaklist: s = s + 'B'
                    else: s = s + ' '
                    if lineno == inspect.getlineno(self.curframe) \
                       and filename == self.curframe.f_code.co_filename:
                        s = s + '->'
                    self.msg_nocr(s + '\t' + line)
                    self.lineno = lineno
        except KeyboardInterrupt:
            pass
        return False

    do_l = do_list

    def do_next(self, arg):
        """n(ext) [count]
Continue execution until the next line in the current function is reached or it returns.

With an integer argument, perform 'next' that many times."""
        if not self.is_running(): return
        try:
            # 0 means stop now or step 1, so we subtract 1.
            self.step_ignore = self.get_pos_int(arg, default=1,
                                                cmdname='next') - 1
        except ValueError:
            return False

        self.stepping = True  # Used in thread debugging
        self.set_next(self.curframe)
        # Tell cmdloop to break out of its loop.
        return True

    do_n = do_next

    def do_p(self, arg):
        """Print the value of the expression. Variables accessible are those of the
environment of the selected stack frame, plus globals. 

The expression may be preceded with /FMT where FMT is one of the
format letters 'c', 'x', 'o', 'f', or 's' for chr, hex, oct, 
float or str respectively.

If the length output string large, the first part of the value is
shown and ... indicates it has been truncated

See also `pp' and `examine' for commands which do more in the way of
formatting."""
        args = arg.split()
        if len(args) > 1 and '/' == args[0][0]:
            fmt = args[0]
            del args[0]
            arg = ' '.join(args)
        else:
            fmt = None
            pass
        try:
            val = self.getval(arg)
            if fmt:
                val = fns.printf(val, fmt)
                pass
            self.msg(self._saferepr(val))
        except:
            pass

    def do_pdef(self, arg):
        """pdef obj

Print the definition header for a callable object.
If the object is a class, print the constructor information.

See also pydoc."""
        args = arg.split()
        if len(args) != 1: return
        obj_name = args[0]
        try:
            obj = eval(arg, self.curframe.f_globals,
                             self.curframe.f_locals)
        except:
            return
        if not callable(obj):
            self.errmsg('Object %s is not callable.' % obj_name)
            return

        if inspect.isclass(obj):
            self.msg('Class constructor information:')
            obj = obj.__init__
        elif type(obj) is types.InstanceType:
            obj = obj.__call__
            pass

        output = print_argspec(obj, obj_name)
        if output is None:
            self.errmsg('No definition header found for %s' % obj_name)
        else:
            self.msg(output)
            pass
        return

    def do_pp(self, arg):
        """pp expression
        Pretty-print the value of the expression."""
        try:
            val = self.getval(arg)
            if type(val) == types.ListType:
                # Handle simple case where list is not nested
                simple = True
                for i in range(len(val)):
                    if not (type(val[i]) in [types.BooleanType, types.FloatType, 
                                         types.IntType,  types.StringType,
                                         types.UnicodeType, types.NoneType,
                                         types.LongType]):
                        simple = False
                        break

                if simple: 
                    self.msg(fns.columnize_array(val, self.width))
                    return False
                
            self.msg(pprint.pformat(val))
        except:
            pass

    def do_pwd(self, arg):
        "Print working directory."
        self.msg('Working directory ' + os.getcwd() + '.')

    def do_pydoc(self, arg):
        """pydoc <name> ...

Show pydoc documentation on something. <name> may be the name of a
Python keyword, topic, function, module, or package, or a dotted
reference to a class or function within a module or module in a
package.  If <name> contains a '/', it is used as the path to a Python
source file to document. If name is 'keywords', 'topics', or
'modules', a listing of these things is displayed.
"""
        sys_path_save = list(sys.path)
        sys_argv_save = list(sys.argv)
        sys.argv      = ['pydoc'] + shlex.split(arg)
        pydoc.cli()
        sys.argv      = sys_argv_save
        sys.path      = sys_path_save
        return False

    def do_python(self, arg_str):
        """python 

Run python as a command subshell.
"""

        # See if python's code module is around
        try:
            from code import interact
        except ImportError:
            self.msg("python code doesn't seem to be importable.")
            return False

        # Python does it's own history thing.
        # Make sure it doesn't damage ours.
        if hasattr(self, 'readline') and self.readline:
            try:
                self.write_history_file()
            except IOError:
                pass

        local = None
        if self.curframe:
            if self.curframe.f_locals:
                local = dict(self.curframe.f_locals)
                local.update(self.curframe.f_globals)
            else:
                local = self.curframe.f_globals
            pass

        if local:
            interact(banner='Pydb python shell', local=local)
        else:
            interact(banner='Pydb python shell')

        # Restore our history if we can do so.
        if hasattr(self, 'readline') and self.readline and self.histfile is not None:
            try:
                self.readline.read_history_file(self.histfile)
            except IOError:
                pass
            return False
        return False

    def do_quit(self, arg):
        """q(uit) or exit - Quit the debugger.  The program being
        executed is aborted."""
        if self.target != 'local':
            self._rebind_output(self.orig_stdout)
            self._rebind_input(self.orig_stdin)
            self._disconnect()
            self.target = 'local'

        sys.settrace(None)
        self._user_requested_quit = True
        self.running              = False
        self.set_quit()

        # Tell cmdloop to break out of its loop.
        return True

    do_q = do_quit

    def do_restart(self, arg):
        """restart - Restart debugger and program via an exec
        call. All state is lost, and new copy of the debugger is used."""

        # We don't proceed with the restart until the action has been
        # ACK'd by any connected clients
        if self.connection != None:
            self.msg('restarting (connection)')
            line = ""
            while not 'ACK:restart_now' in line:
                line = self.connection.readline()
            self.do_rquit(None)
        else:
            if self._sys_argv[0]:
                self.msg("Re exec'ing:\n\t%s" % self._sys_argv)
                os.execvp(self._sys_argv[0], self._sys_argv)
            else:
                self.msg("No exectuable file specified.")
        return False
        

    def do_return(self, arg):
        """Make selected stack frame return to its caller. Control
        remains in the debugger, but when you continue execution will
        resume at the return statement found inside the subroutine or
        method.  At present we are only able to perform this if we are
        in a subroutine that has a 'return' statement in it."""
        if not self.is_running(): return
        frame = self.curframe

        if '?' == frame.f_code.co_name and not '__args__' in frame.f_locals:
            self.errmsg("I don't see that we are in a subroutine.")
            return

        while True and not self.noninteractive:
            try:
                # reply = raw_input('Make %s return now? (y or n) ')
                reply = raw_input('Return now? (y or n) ').strip()
            except EOFError:
                reply = 'no'
                reply = reply.strip().lower()
            if reply in ('y', 'yes'):
                break
            elif reply in ('n', 'no'):
                return
            else:
                self.msg("Please answer y or n.")

        co = frame.f_code
        code = co.co_code
        labels = dis.findlabels(code)
        linestarts = dict(dis.findlinestarts(co))

        i=frame.f_lasti
        last_line = inspect.getlineno(frame)
        # last_stmt = i
        # print "++i: %d, len(code): %d" % (i, len(code))
        while i < len(code):
            i += 1
            if i in labels:
                # print "++last_stmt %d" % i
                # last_stmt = i
                last_line = None
            if i in linestarts and i > 0:
                # print "++last_line %d" % linestarts[i]
                last_line = linestarts[i]
            if 'RETURN_VALUE' == op_at_frame(frame, i):
                break

        if i == len(self.stack) or last_line is None:
            self.msg("Sorry; a return statement was not found.")
            return

        # print "++i: %d, last_stmt %d, line: %d " % (i, last_stmt, last_line)
        self.do_jump(last_line, "Return")
        return False

    def do_run(self, arg_str):
        """run [args...]

        Run or "soft" restart the debugged Python program. If a string
is supplied, it is splitted with "shlex" but preserving embedded quotes.
The result is used as the new sys.argv.  History, breakpoints, actions
and debugger options are preserved. R is a alias for 'run'.

See also 'restart' for an exec-like restart."""
        if not self._program_sys_argv:
            self.errmsg("No Python program registered.")
            self.errmsg("Perhaps you want to use the 'file' command?")
            return
        if arg_str:
            argv_start = self._program_sys_argv[0:1]
            self._program_sys_argv = arg_split(arg_str)
            self._program_sys_argv[:0] = argv_start

        raise Restart

    do_R = do_run

    def do_save(self, arg):
        """save [all|break|settings] [filename]
        Save specified settings to a file as a script
Use the 'source' command in another debug session to restore them."""
        args = arg.split()
        actions = ['all', 'break', 'settings']
        filename = os.path.expanduser("~/pydb-restart.txt")
        if 0 == len(args):
            what = 'all'
        elif 1 == len(args):
            if args[0] in actions:
                what = args[0]
            else:
                filename = os.path.expanduser(args[0])
                what = 'all'
        elif 2 == len(args):
            what = args[0]
            if args[0] not in actions:
                self.errmsg("Action has to be 'all', 'break' or 'settings; " 
                            "got '%s'." % args[0])
                return False
            filename = os.path.expanduser(args[1])
        else: 
            # len(args) > 2:
            self.errmsg("Expecting 0-2 arguments, got %d." % len(args))
            return False
        restart_file = open(filename, 'w')
        what_str = ''
        if what in ('all', 'break'):
            lines = self.output_break_commands()
            restart_file.write("\n".join(lines) + "\n")
            what_str = 'Breakpoints'
        if what in ('all', 'settings'):
            if '' == what_str:
                what_str = 'Settings'
            else:
                what_str = 'Settings and breakpoints'
            for subcommand in self.setcmds.list():
                if subcommand in ['args', 'debug-pydb', 'history', 'logging', 
                                  'prompt', 'trace-commands', 'warnoptions']: 
                                  continue
                # commands that have lots of output we can't handle right now.
                if not self.showcmds.subcmds[subcommand]['in_list']:
                    continue
                val = eval('self.get_%s()' % subcommand)
                restart_file.write('set %s %s\n' % (subcommand, val))
        if what_str != '':
            restart_file.close()
            self.msg('%s saved to file %s' % (what_str, restart_file.name))
            return False
        return False

    def do_set(self, arg):
        """See help_set"""
        args = arg.split()
        if len(args) == 1 and 'warnoptions'.startswith(args[0]):
            self.setcmds.do(self, args[0], args)
            return
        if len(args) < 2:
            self.errmsg("Expecting at least 2 arguments, got %d." % len(args))
            return False
        self.setcmds.do(self, args[0], args)
        return False

    def do_shell(self, arg):
        """Execute the rest of the line as a shell command."""
        os.system(arg)
        return False

    def do_show(self, arg):

        """Generic command for showing things about the debugger.  You
        can give unique prefix of the name of a subcommand to get info
        about just that subcommand."""

        if not arg:
            for subcommand in self.showcmds.list():
                # Some commands have lots of output.
                # they are excluded here because 'in_list' is false.
                if self.showcmds.subcmds[subcommand]['in_list']:
                    self.msg_nocr("%s: " % subcommand)
                    self.do_show(subcommand)
            return False

        if self._re_linetrace_delay.match(arg):
            self.msg("line trace delay is %s. (In seconds)"
                     % self.linetrace_delay)
        else:
            args = arg.split()
            self.showcmds.do(self, args[0], args)

        return False
            
    def do_signal(self, arg):
        """signal [signum|signame]

Send a signal to the debugged process.
"""
        if arg =='':
            signum = 0
        else:
            try: 
                signum = int(eval(arg))
                if sighandler.lookup_signame(signum) == None:
                    self.msg("Signal number %d not a known signal number."
                             % signum)
                    return
            except ValueError:
                signum = sighandler.lookup_signum(arg)
                if signum == None:
                    self.msg("Signal name %s not a known signal name."
                             % arg)
                    return
        os.kill(os.getpid(), signum)
        return False
        
    def do_skip(self, arg):
        """skip [count]

        Set the next line that will be executed. The line must be within
        the stopped or bottom-most execution frame frame."""

        if not self.is_running(): return None

        if self.curindex + 1 != len(self.stack):
            self.errmsg("You can only skip within the bottom frame.")
            return None

        if self.curframe.f_trace is None:
            self.errmsg("Sigh - operation can't be done here.")
            return None
        
        try:
            count = self.get_pos_int(arg, default=1, cmdname='skip')
        except ValueError:
            return None
        co = self.curframe.f_code
        offset = self.curframe.f_lasti
        if count is None: return False
        lineno = bytecode.next_linestart(co, offset, count)

        if lineno < 0:
            self.errmsg('No next line found')
            return False

        try:
            # Set to change position, update our copy of the stack,
            # and display the new position
            self.curframe.f_lineno = lineno
            self.stack[self.curindex] = self.stack[self.curindex][0], lineno
            self.print_location()
        except ValueError, e:
            self.errmsg('skip failed: %s' % e)
        return None

    def do_source(self, arg):
        """source [-v] FILE
        Read debugger commands from a file named FILE.
        Optional -v switch (before the filename) causes each command in
        FILE to be echoed as it is executed.
        Note that the file '.pydbrc' is read automatically
        in this way when pydb is started.

        An error in any command terminates execution of the command
        file and control is returned to the console."""
        args = arg.split()
        verbose=False
        if len(args) == 2 and args[0] == '-v': 
            arg=args[1]
            verbose=True
        self.setup_source(os.path.expanduser(arg), True);
        rc = self.execRcLines(verbose)
        if rc == 1:  return True
        return False

    def do_step(self, arg):
        """s(tep) [count]
Execute the current line, stop at the first possible occasion
(either in a function that is called or in the current function).

With an integer argument, step that many times."""
        if not self.is_running(): return None
        try:
            # 0 means stop now or step 1, so we subtract 1.
            self.step_ignore = self.get_pos_int(arg, default=1,
                                                cmdname='step') - 1
        except ValueError:
            return

        self.stepping = True  # Used in thread debugging
        self.set_step()
        # Tell cmdloop to break out of its loop.
        return True

    do_s = do_step

    def do_tbreak(self, arg, thread_name=None):
        """tbreak  [ ([filename:]lineno | function) [, condition] ]
        Set a temporary breakpoint. Arguments are like the "break" command.
        Like "break" except the breakoint is only temporary,
        so it will be deleted when hit."""
        self.do_break(arg, 1, thread_name)

    def do_unalias(self, arg):
        """unalias name
Deletes the specified alias."""
        args = arg.split()
        if len(args) == 0: return
        if args[0] in self.aliases:
            del self.aliases[args[0]]
        return False

    # Print a traceback starting at the top stack frame.
    # The most recently entered frame is printed last;
    # this is different from dbx and gdb, but consistent with
    # the Python interpreter's stack trace.
    # It is also consistent with the up/down commands (which are
    # compatible with dbx and gdb: up moves towards 'main()'
    # and down moves towards the most recent stack frame).

    def do_undisplay(self, arg):
        """Cancel some expressions to be displayed when program stops.
        Arguments are the code numbers of the expressions to stop displaying.
        No argument means cancel all automatic-display expressions.
        "delete display" has the same effect as this command.
        Do "info display" to see current list of code numbers."""

        if arg:
            args = arg.split()
            if len(args) == 1:
                self.display.clear()
                return
            for i in args:
                i = self.get_an_int(i, 'index %r is not a number' % i)
                if i is not None:
                    if not self.display.delete_index(i):
                        self.errmsg("No display number %d." % i)
                        return
                    pass
                pass
        return False

    def do_up(self, arg):
        """up [count]
        Move the current frame one level up in the stack trace
        (to an older frame).

        If using gdb dialect up matches the gdb: 0 is the most recent
        frame.  Otherwise we match Python's stack: 0 is the oldest
        frame.  """

        try:
            count = self.get_int(arg, cmdname="up")
        except ValueError:
            return
        if self.gdb_dialect:
            count = -count
        self.__adjust_frame(pos=count, absolute_pos=False)
        return False

    def do_whatis(self, arg):
        """whatis arg
Prints the type of the argument which can be a Python expression."""
        try:
            if not self.curframe:
                # ?? Should we have set up a dummy globals
                # to have persistence?
                value = eval(arg, None, None)
            else:
                value = eval(arg, self.curframe.f_globals,
                             self.curframe.f_locals)
        except:
            t, v = sys.exc_info()[:2]
            if type(t) == types.StringType:
                exc_type_name = t
            else: exc_type_name = t.__name__
            if exc_type_name == 'NameError':
                self.errmsg("Name Error: %s" % arg)
            else:
                self.errmsg("%s: %s" % (exc_type_name, self._saferepr(v)))
            return False
        if inspect.ismethod(value):
            self.msg('method %s%s' %
                     (value.func_code.co_name,
                       inspect.formatargspec(inspect.getargspec(value))))
            if inspect.getdoc(value):
                self.msg('%s:\n%s' %
                         (value, inspect.getdoc(value)))
            return False
        elif inspect.isfunction(value):
            self.msg('function %s%s' %
                     (value.func_code.co_name,
                       inspect.formatargspec(inspect.getargspec(value))))
            if inspect.getdoc(value):
                self.msg('%s:\n%s' %
                         (value, inspect.getdoc(value)))
            return False
        # None of the above...
        self.msg(type(value))
        return False

    def do_where(self, arg):
        """where [count]

        Print a stack trace, with the most recent frame at the top.
        With a positive number, print at most many entries.
        An arrow indicates the 'current frame', which determines the
        context of most commands.  'bt' and 'T' are short command
        names for this."""

        try:
            count = self.get_pos_int(arg, default=None, cmdname="where")
        except ValueError:
            return False

        if not self.curframe:
            self.msg("No stack.")
            return False
        print_stack_trace(self, count)
        return False

    do_T = do_bt = do_where

    def do_EOF(self, arg):
        """EOF
Handles the receipt of EOF as a command."""
        self.msg("")
        self._user_requested_quit = True
        self.set_quit()

        # Tell cmdloop to break out of its loop.
        return True

    #########################################################
    # Help methods (derived from pydb.doc or vice versa)
    #########################################################

    for fn in ('EOF',     'alias',     'break',
               'cd',      'clear',     'condition',   'continue',
               'debug',   'disable',   'delete'   ,   'disassemble',
               'display', 'down',      'enable',      'examine',
               'finish',  'frame',     'help',
               'ignore',  'info',      'jump',        'list',
               'next',    'p',         'pp',          'pwd',    'quit',
               'restart', 'retval',    'run',
               'set',     'show',      'shell',       'source', 'step',
               'tbreak',  'unalias',   'undisplay',   'up',
               'whatis',  'where'):
        exec 'def help_%s(self, *arg): self.msg(self.do_%s.__doc__)' \
             % (fn, fn)

    # Is this the right way to do this?
    ## Remove duplicate short names
    ## help_h = help_help
    ## help_R = help_run
    ## help_bt = help_T = help_where

    def help_commands(self, *arg):
        print """commands [bpnumber]
>...
>end
(Pydb)

Set commands to be executed when a breakpoint is hit.
Give breakpoint number as the argument after "commands".
With no bpnumber argument, commands refers to the last one set.
The commands themselves follow starting on the next line.
Type a line containing "end" to terminate the commands.

To remove all commands from a breakpoint, type commands and
follow it immediately with end; that is, give no commands.

You can use breakpoint commands to start your program up
again. Simply use the continue command, or step, or any other
command that resumes execution.

Specifying any command resuming execution (currently continue, step,
next, return, jump, and quit) terminates the command list as if that
command was immediately followed by 'end'.  This is because any time
you resume execution (even with a simple next or step), you may
encounter another breakpoint--which could have its own command list,
leading to ambiguities about which list to execute.

If you use the 'silent' command in the command list, the
usual message about stopping at a breakpoint is not printed.
This may be desirable for breakpoints that are to print a
specific message and then continue.  If none of the other
commands print anything, you see no sign that the breakpoint
was reached.
"""

    def help_exec(self, *arg):
        self.msg("""(!) statement
        Execute the (one-line) statement in the context of
        the current stack frame.
        The exclamation point can be omitted unless the first word
        of the statement resembles a debugger command.
        To assign to a global variable you must always prefix the
        command with a 'global' command, e.g.:
        %sglobal list_options; list_options = ['-l']
        %s""" % (self.prompt, self.prompt))
        return

    # Note: format of help is compatible with ddd.
    def help_info(self, args):
        """Generic command for showing things about the program being debugged."""
        if len(args) == 0:
            self.infocmds.help(self, '')
        else:
            self.infocmds.help(self, args[0])
            return
        return

    # Note: format of help is compatible with ddd.
    def help_set(self, args):
        """This command modifies parts of the debugger environment.
You can see these environment settings with the 'show' command."""
        if len(args) == 0:
            self.setcmds.help(self, '')
        else:
            self.setcmds.help(self, args[0])
            return
        return

    # Note: format of help is compatible with ddd.
    def help_show(self, args):
        """Generic command for showing things about the debugger."""
        if len(args) == 0:
            self.showcmds.help(self, '')
        else:
            self.showcmds.help(self, args[0])
            return
        return

    def help_unalias(self):
        print """unalias name
Deletes the specified alias."""
        return

    ####### End of help section ########
#
# Local variables:
#  mode: Python
# End:
