#!/usr/bin/python -t
# $Id: test-fns.py.in,v 1.1 2007/11/01 09:20:31 rockyb Exp $ -*- Python -*-

# This unit test doesn't use any of the debugger code. It is meant solely
# to test the connection classes.

import os, sys, thread, time, unittest

top_builddir = ".."
if top_builddir[-1] != os.path.sep:
    top_builddir += os.path.sep
sys.path.insert(0, os.path.join(top_builddir, 'pydb'))
top_srcdir = ".."
if top_srcdir[-1] != os.path.sep:
    top_srcdir += os.path.sep
sys.path.insert(0, os.path.join(top_srcdir, 'pydb'))

import fns

class TestFns(unittest.TestCase):

    def test_show_onoff(self):
       """Test of fns.show_onoff()"""
       self.assertEqual(fns.show_onoff(True), 'on')
       self.assertEqual(fns.show_onoff(False), 'off')

    def test_printf(self):
       """Test of fns.printf()"""
       self.assertEqual( fns.printf(31, "/o"), '037')
       self.assertEqual( fns.printf(31, "/t"), '00011111')
       self.assertEqual( fns.printf(33, "/c"), '!')
       self.assertEqual( fns.printf(33, "/x"), '0x21')

    def test_file_pyc2py(self):
       """Test file_pyc2py()"""
       self.assertEqual( "gcd.py", fns.file_pyc2py("gcd.pyo"),
                         "xx.pyo should transform to xx.py")
       self.assertEqual( "/tmp/gcd.py", fns.file_pyc2py("/tmp/gcd.pyc"),
                         "xx.pyc should transform to xx.py")
       self.assertEqual( "../gcd.py", fns.file_pyc2py("../gcd.py"),
                         "Test null transform")

    def test_whence_file(self):
       """Test whence_file()"""
       fname = os.path.join(os.curdir, "thisfilenotthere")
       self.assertEqual( fname, fns.whence_file(fname),
                         "whence should not change due to sep in name" )

       os.environ["PATH"] = ""
       fname = "gcd.py"
       self.assertEqual( fname, fns.whence_file(fname),
                         "Test of whence_file path expansion - not found " )
       test_dir = os.path.join(top_srcdir, "test")
       os.environ["PATH"] = test_dir
       fname = "gcd.py"
       expand_fname = os.path.join(test_dir, fname)
       self.assertEqual( expand_fname, fns.whence_file(fname),
                         "Test of whence_file path expansion - found" )

    def test_columnize(self):
        self.assertEqual("['one', 'two', 'three']", 
                         fns.columnize_array(["one", "two", "three"]))
        self.assertEqual("[oneitem]", fns.columnize_array(["oneitem"]))
        self.assertEqual(
"""['one', 'two', 'three', '4ne', '5wo', '6hree', '7ne', '8wo', '9hree'
 '10e', '11o', '12ree', '13e', '14o', '15ree', '16e', '17o', '18ree'
 '19e', '20o', '21ree', '22e', '23o', '24ree', '25e', '26o', '27ree'
 '28e', '29o', '30ree', '31e', '32o', '33ree', '34e', '35o', '36ree'
 '37e', '38o', '39ree', '40e', '41o', '42ree', '43e', '44o', '45ree'
 '46e', '47o', '48ree', 'one'...]""",
                 fns.columnize_array([
                    "one", "two", "three",
                    "4ne", "5wo", "6hree",
                    "7ne", "8wo", "9hree",
                    "10e", "11o", "12ree",
                    "13e", "14o", "15ree",
                    "16e", "17o", "18ree",
                    "19e", "20o", "21ree",
                    "22e", "23o", "24ree",
                    "25e", "26o", "27ree",
                    "28e", "29o", "30ree",
                    "31e", "32o", "33ree",
                    "34e", "35o", "36ree",
                    "37e", "38o", "39ree",
                    "40e", "41o", "42ree",
                    "43e", "44o", "45ree",
                    "46e", "47o", "48ree",
                    "one", "two", "three"]))


if __name__ == '__main__':
    unittest.main()
