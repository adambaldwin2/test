import random
import unittest
import string

from guppy import hpy

from pybloom import BloomFilter
from pybloom import ScalableBloomFilter

class TestBloomFilter(unittest.TestCase):

    def test_bloom_int(self):
        a = hpy().heap()
        a = hpy().heap()
        f = BloomFilter(capacity=10000, error_rate=0.001)
        b = hpy().heap()
        print b.diff(a)

        for i in xrange(0, f.capacity):
             _ = f.add(i)

        for i in xrange(0, f.capacity / 2 ):
            r = random.randint(0,f.capacity-1)
            self.assertEqual(r in f, True)

        for i in xrange(0, f.capacity / 2 ):
            r = random.randint(f.capacity,f.capacity * 2)
            self.assertEqual(r in f, False)
        
    def test_bloom_string(self):
        f = BloomFilter(capacity=10000, error_rate=0.001)

        for i in xrange(0, f.capacity):
            rnd = ''.join(random.choice(string.letters) for i in xrange(40))
            _ = f.add(rnd)

        self.assertEqual(rnd in f, True)

        for i in string.letters:
            self.assertEqual(i in f, False)

        self.assertEqual(rnd in f, True)

class TestScalableBloomFilter(unittest.TestCase):

    def test_bloom_int(self):
        f = ScalableBloomFilter(mode=ScalableBloomFilter.SMALL_SET_GROWTH)

        for i in xrange(0, 10000):
             _ = f.add(i)

        for i in xrange(0, 10000):
            self.assertEqual(i in f, True)

        for i in xrange(0, 10000 / 2 ):
            r = random.randint(0,10000-1)
            self.assertEqual(r in f, True)

        for i in xrange(0, 10000 / 2 ):
            r = random.randint(10000,10000 * 2)
            self.assertEqual(r in f, False)

    def test_bloom_string(self):
        f = ScalableBloomFilter(mode=ScalableBloomFilter.SMALL_SET_GROWTH)

        for i in xrange(0, 10000):
            rnd = ''.join(random.choice(string.letters) for i in xrange(40))
            _ = f.add(rnd)

        self.assertEqual(rnd in f, True)

        for i in string.letters:
            self.assertEqual(i in f, False)

        self.assertEqual(rnd in f, True)

if __name__ == '__main__':
    unittest.main()

