#!/usr/bin/python -t
# $Id: test-import.py.in,v 1.2 2008/12/10 13:31:26 rockyb Exp $ -*- Python -*-
"Unit test of 'import pydb'"
import os, sys, unittest

top_builddir = ".."
if top_builddir[-1] != os.path.sep:
    top_builddir += os.path.sep
top_srcdir = ".."
if top_srcdir[-1] != os.path.sep:
    top_srcdir += os.path.sep

builddir     = "."
if builddir[-1] != os.path.sep:
    builddir += os.path.sep

srcdir = "."
if srcdir[-1] != os.path.sep:
    srcdir += os.path.sep

class PdbTests(unittest.TestCase):

    def test_import(self):
        """Test that 'import pydb' works"""
        cmd = ("/usr/bin/python -c 'import os, sys; " + 
        "sys.path.insert(0, \"%s\"); " +
        "sys.path.insert(0, \"%s\"); " +
        "import pydb'" ) % (top_builddir, top_srcdir)
        rc = os.system(cmd) >> 8
        self.assertEqual(0, rc, "python import pydb")
        return

if __name__ == "__main__":
    unittest.main()
