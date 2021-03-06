#!/usr/bin/python -t
# $Id: test-trace.py.in,v 1.4 2008/12/08 00:40:57 rockyb Exp $ -*- Python -*-
"Unit test of program execution tracing using the Extended Python debugger "
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

def run_debugger(testname, pythonfile, pydb_opts='', args='', 
                 outfile=None, need_25=True):
    global srcdir, builddir, pydir

    if sys.hexversion >= 0x02050000 and need_25:
        rightfile   = os.path.join(srcdir, 'data',
                                   "%s-2.5.right" % testname)
    elif (sys.version_info[0:2] == (2, 4) and sys.version_info[3] == 'final'
        and need_25):
        rightfile   = os.path.join(srcdir, 'data',
                                   "%s-2.4-final.right" % testname)
    else:
        rightfile   = os.path.join(srcdir, 'data', 
                                   "%s.right" % testname)

    outfile_opt = ''
    if outfile is None:
        outfile     = os.path.join(builddir, "%s.out" % testname)
        outfile_opt = '--output=%s ' % outfile

    # print "builddir: %s, cmdfile: %s, outfile: %s, rightfile: %s" % \
    # (builddir, cmdfile, outfile, rightfile)

    if os.path.exists(outfile): os.unlink(outfile)

    os.environ['PYTHONPATH']=os.pathsep.join(sys.path)
    cmd = "%s %s %s %s %s" % \
          (pydb_path, outfile_opt, pydb_opts, pythonfile, args)
    
    os.system(cmd)
    fromfile  = rightfile
    fromdate  = time.ctime(os.stat(fromfile).st_mtime)
    fromlines = open(fromfile, 'U').readlines()[0:-2]
    tofile    = outfile
    todate    = time.ctime(os.stat(tofile).st_mtime)
    tolines   = open(tofile, 'U').readlines()[0:-2]
    diff = list(difflib.unified_diff(fromlines, tolines, fromfile,
                                     tofile, fromdate, todate))
    if len(diff) == 0:
        os.unlink(outfile)
    for line in diff:
        print line,
    return len(diff) == 0
    
class PdbTests(unittest.TestCase):

    def test_linetrace(self):
        """Test running program tracing: --trace and -X options"""
        for trace_opt in ['--trace', '-X']:
            result=run_debugger(testname='trace',
                                pydb_opts='%s --basename' % trace_opt,
                                pythonfile='%shanoi.py' % srcdir)
            self.assertEqual(True, result, 
                             "hanoi line trace (%s) output comparision" % 
                             trace_opt)
        

    def test_fntrace(self):
        """Test running program tracing: --fntrace and -X options"""
        for trace_opt in ['--fntrace', '-F']:
            result=run_debugger(testname='fntrace',
                                pydb_opts='%s --basename' % trace_opt,
                                pythonfile='%sgcd.py' % srcdir,
                                args='4 6', need_25 = False)
        self.assertEqual(True, result, 
                         "gcd function trace (%s) output comparision" %
                         trace_opt)
        

    def test_trace_compiled(self):
        """Test running program tracing: --trace option after compiling"""
        opt_file = "%shanoi.pyc" % srcdir
        if os.path.exists(opt_file): os.unlink(opt_file)
        import py_compile
        py_compile.compile("%shanoi.py" % srcdir)
        if os.path.exists(opt_file):
            result=run_debugger(testname='trace',
                                pydb_opts='--trace --basename',
                                pythonfile=opt_file)
            self.assertEqual(True, result,
                             "compiled hanoi trace output comparision")
        

if __name__ == "__main__":
    unittest.main()
