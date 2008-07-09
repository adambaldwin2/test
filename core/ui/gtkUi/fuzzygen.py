'''
fuzzygen.py

Copyright 2008 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
import re
try:
    from core.controllers.w3afException import w3afException
except ImportError:
    # this is to easy the test when executing this file directly
    w3afException = Exception

REPP = re.compile("\$.*?\$")

class FuzzyError(w3afException): pass

# Syntax rules:
# 
# - the "$" is the delimiter
# 
# - to actually include a "$", use "$$"
#
# - if you write "$something$", the "something" will be evaluated with 
#   eval, having the "string" module already imported (eg: 
#   "$range(1,5,2)$", "$string.lowercase$").

class FuzzyGenerator(object):
    '''Handles two texts with the fuzzy syntax.

    @author: Facundo Batista <facundobatista =at= taniquetil.com.ar>
    '''
    def __init__(self, txt1, txt2):
        # separate the sane and replaceable info
        torp1, self.sane1 = self._dissect(txt1)
        torp2, self.sane2 = self._dissect(txt2)

        # generate the generators, :)
        self.genr1 = [self._genIterator(x) for x in torp1]
        self.genr2 = [self._genIterator(x) for x in torp2]

        # if one of them is empty, put a dummy
        if not self.genr1:
            self.genr1 = [[]]
        if not self.genr2:
            self.genr2 = [[]]

    def _genIterator(self, text):
        namespace = {"string":__import__("string")}
        try:
            it = eval(text, namespace)
        except Exception, e:
            msg = "%s: %s (generated from %r)" % (e.__class__.__name__, e, text)
            raise FuzzyError(msg)

        try:
            iter(it)
        except TypeError:
            raise FuzzyError("%r is not iterable! (generated from %r)" % (it,text))
        return it
        
    def _dissect(self, txt):
        # remove the double $$
        txt = txt.replace("$$", "\x00")

        # separate sane texts from what is to be replaced 
        toreplace = REPP.findall(txt)
        saneparts = REPP.split(txt)
        
        # transform $$ for $
        for i,part in enumerate(toreplace):
            if "\x00" in part:
                toreplace[i] = part.replace("\x00", "$")
        for i,part in enumerate(saneparts):
            if "\x00" in part:
                saneparts[i] = part.replace("\x00", "$")

        # extract border $
        toreplace = [x[1:-1] for x in toreplace]
    
        return toreplace, saneparts

    def generate(self):
        for x in self._possib(self.genr1):
            full1 = self._build(self.sane1, x)
            for y in self._possib(self.genr2):
                full2 = self._build(self.sane2, y)
                yield (full1, full2)

    def _build(self, sane, vals):
        if vals is None:
            return sane[0]
        full = []
        for x,y in zip(sane, vals):
            full.append(str(x))
            full.append(str(y))
        full.append(str(sane[-1]))
        return "".join(full)

    def _possib(self, generat, constr=[]):
        pos = len(constr)
        if not generat[pos]:
            yield None
        for elem in generat[pos]:
            if pos+1 == len(generat):
                yield constr+[elem]
            else:
                for val in self._possib(generat, constr+[elem]):
                    yield val

        
if __name__ == "__main__":
    import unittest

    class TestAll(unittest.TestCase):
        def test_simple_doubledollar(self):
            fg = FuzzyGenerator("Hola $$mundo\ncruel", "")
            self.assertEqual(fg.sane1, ["Hola $mundo\ncruel"])
            
            fg = FuzzyGenerator("Hola $$mundo\ncruel$$", "")
            self.assertEqual(fg.sane1, ["Hola $mundo\ncruel$"])
            
            fg = FuzzyGenerator("Hola $$mundo\ncruel$$asdfg$$$$gh", "")
            self.assertEqual(fg.sane1, ["Hola $mundo\ncruel$asdfg$$gh"])

        def test_generations(self):
            fg = FuzzyGenerator("$range(2)$ dnd$'as'$", "pp")
            self.assertEqual(list(fg.generate()), [
                ('0 dnda', 'pp'), ('0 dnds', 'pp'), ('1 dnda', 'pp'), ('1 dnds', 'pp')])
        
            fg = FuzzyGenerator("$range(2)$ dnd$'as'$", "pp$string.lowercase[:2]$")
            self.assertEqual(list(fg.generate()), [
                ('0 dnda', 'ppa'), ('0 dnda', 'ppb'), ('0 dnds', 'ppa'), ('0 dnds', 'ppb'),
                ('1 dnda', 'ppa'), ('1 dnda', 'ppb'), ('1 dnds', 'ppa'), ('1 dnds', 'ppb'),
            ])
        
        def test_noniterable(self):
            self.assertRaises(FuzzyError, FuzzyGenerator, "", "aa $3$ bb")
            self.assertRaises(FuzzyError, FuzzyGenerator, "", "aa $[].extend([1,2])$ bb")

        def test_inside_doubledollar(self):
            fg = FuzzyGenerator("GET http://localhost/$['aaa$$b', 'b$$ccc']$ HTTP/1.0", "")
            self.assertEqual(list(fg.generate()), [
                ("GET http://localhost/aaa$b HTTP/1.0", ""),
                ("GET http://localhost/b$ccc HTTP/1.0", ""),
                                ])

    unittest.main()
