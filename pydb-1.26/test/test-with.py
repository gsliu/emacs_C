#!/usr/bin/python -t
# $Id: test-with.py.in,v 1.7 2008/12/10 13:31:26 rockyb Exp $ -*- Python -*-
"""Unit test of the bug in using 'info local' when inside a "with" command."""
import difflib, os, time, sys, unittest

top_builddir = ".."
if top_builddir[-1] != os.path.sep:
    top_builddir += os.path.sep
sys.path.insert(0, os.path.join(top_builddir, 'pydb'))
top_srcdir = ".."
if top_srcdir[-1] != os.path.sep:
    top_srcdir += os.path.sep
sys.path.insert(0, os.path.join(top_srcdir, 'pydb'))

builddir     = "."
if builddir[-1] != os.path.sep:
    builddir += os.path.sep

srcdir = "."
if srcdir[-1] != os.path.sep:
    srcdir += os.path.sep

pydir        = os.path.join(top_builddir, "pydb")
pydb_short   = "pydb.py"
pydb_path    = os.path.join(pydir, pydb_short)

def run_debugger(testname, pythonfile, pydb_opts='', args='', rightfile=None,
                 need_26=False):
    global srcdir, builddir, pydir

    if rightfile is None:
        rightfile   = os.path.join(builddir, 'data', "%s.right" % testname)

    os.environ['PYTHONPATH']=os.pathsep.join(sys.path)
    cmdfile     = os.path.join(srcdir, "%s.cmd"   % testname)
    outfile     = "%s.out" % testname
    outfile_opt = '--output=%s ' % outfile

    # print "builddir: %s, cmdfile: %s, outfile: %s, rightfile: %s" % \
    # (builddir, cmdfile, outfile, rightfile)

    if os.path.exists(outfile): os.unlink(outfile)

    cmd = "%s --command %s %s %s %s %s" % \
          (pydb_path, cmdfile, outfile_opt, pydb_opts, args, pythonfile)
    
    os.system(cmd)
    fromfile  = rightfile
    fromdate  = time.ctime(os.stat(fromfile).st_mtime)
    fromlines = open(fromfile, 'U').readlines()[0:-1]
    tofile    = outfile
    todate    = time.ctime(os.stat(tofile).st_mtime)
    tolines   = open(tofile, 'U').readlines()[0:-1]
    if not need_26:
        tolines[4]= tolines[4][0:74] + "\n"
    diff = list(difflib.unified_diff(fromlines, tolines, fromfile,
                                     tofile, fromdate, todate))
    if len(diff) == 0:
        os.unlink(outfile)
    for line in diff:
        print line,
    return len(diff) == 0
    
class PdbTests(unittest.TestCase):

    def test_with(self):
        """Test running bug running "info local" inside a "with" command"""
        if sys.hexversion >= 0x02050000:
            if sys.hexversion >= 0x02060000:
                need_26 = True
                rightfile = os.path.join(srcdir, 'data',
                                         "withbug-2.6.right")
            else:
                need_26 = False
                rightfile = os.path.join(srcdir, 'data',
                                         "withbug.right")
            result=run_debugger(testname='withbug', 
                                pythonfile='%swithbug.py' % srcdir,
                                pydb_opts='--basename',
                                rightfile=rightfile, need_26=need_26)
            self.assertEqual(True, result, "pydb 'withbug' command comparision")
        self.assertTrue(True, 'With test skipped - not 2.5')
        return

if __name__ == "__main__":
    unittest.main()
