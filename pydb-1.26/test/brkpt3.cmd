# 
# Test of breakpoint handling
# $Id: brkpt3.cmd.in,v 1.1 2007/02/13 11:42:54 rockyb Exp $
#
set basename on
set trace-commands on
###############################################################
### Test bad command parameters
###############################################################
# Non integer argument
commands a
# No such breakpoint number
commands 5
###############################################################
### Test valid command. Note that in order to do this
### here we need to use the "source" command so that
### input doesn't get confused.
### FIXME: somehow output isn't coming out. 
###        but at least we're testing part
###        parsing to the "end"
###############################################################
break 28
cd .
source comm1.cmd
continue
break 31
source comm2.cmd
cd .
continue
quit
