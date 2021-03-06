#!/usr/bin/python -t
# $Id: test-complete.py.in,v 1.4 2009/02/09 09:28:39 rockyb Exp $ -*- Python -*-

import os, sys, unittest

try:
    import readline 
except ImportError:
    print "Completion test skipped - no readline"
    sys.exit(0)

top_builddir = ".."
if top_builddir[-1] != os.path.sep:
    top_builddir += os.path.sep
sys.path.insert(0, os.path.join(top_builddir, 'pydb'))
top_srcdir = ".."
if top_srcdir[-1] != os.path.sep:
    top_srcdir += os.path.sep
sys.path.insert(0, os.path.join(top_srcdir, 'pydb'))

from complete import list_completions, all_completions

class TestComplete(unittest.TestCase):

    def test_list_completions(self):
        c=[]; seen={}
        l=["a", "an", "another", "also", "boy"]
        self.assertEqual(list_completions(l, "a",  seen, c),
                         ['a', 'an', 'another', 'also'])
        self.assertEqual(list_completions(l, "b", seen, c),
                         ['a', 'an', 'another', 'also', 'boy'])
        c=[]; seen={}
        self.assertEqual(list_completions(l, "a",  seen, c, "foo "),
                         ['foo a', 'foo an', 'foo another', 'foo also'])
        c=[]; seen={}
        self.assertEqual(list_completions(l, "an", seen, c), ['an', 'another'])
        c=[]; seen={}
        self.assertEqual(list_completions(l, "b",  seen, c),  ['boy'])
        c=[]; seen={}
        self.assertEqual(list_completions(l, "be", seen, c), [])
        return

    def test_all_completions(self):
        import pydb
        dbg = pydb.Pdb()
        dbg.curframe = None
        self.assertEqual( all_completions(dbg, "s"),
            ['s', 'save', 'set', 'shell', 'show', 'signal', 'skip', 
             'source', 'step'])
        self.assertEqual( all_completions(dbg, "set l"),
                          ['set linetrace', 'set listsize', 'set logging'])
        self.assertEqual( all_completions(dbg, "set l", False),
                          ['linetrace', 'listsize', 'logging'])
        return
    
if __name__ == '__main__':
    unittest.main()
