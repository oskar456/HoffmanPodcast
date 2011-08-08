#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class StreamTee:   
    """Intercept a stream.
    
    Invoke like so:
    sys.stdout = StreamTee(sys.stdout)
    
    See: grid 109 for notes on older version (StdoutTee).
    """
    
    def __init__(self, target):
        self.target = target
    
    def write(self, s):
        s = self.intercept(s)
        self.target.write(s)

    def flush(self):
        self.target.flush()
    
    def intercept(self, s):
        """Pass-through -- Overload this."""
        return s


class TranslitFilter(StreamTee):
    """Convert string traffic to to something safe."""
    def __init__(self, target):
        StreamTee.__init__(self, target)
        self.encoding = 'utf-8'
        self.errors = 'replace'
        self.encode_to = self.target.encoding
    def intercept(self, s):
        import unicodedata
        # Expand pre-combined characters into base+combinator
        s1 = unicodedata.normalize("NFD", s)
        r = []
        for c in s1:
            # add all non-combining characters
            if not unicodedata.combining(c):
                r.append(c)
        return "".join(r)



if __name__ == '__main__':
	import sys
	print("Current STDOUT encoding: {}".format(sys.stdout.encoding))
	if sys.stdout.encoding != 'UTF-8':
		sys.stdout = TranslitFilter(sys.stdout)
	print("ě+ščřžýáíé")
