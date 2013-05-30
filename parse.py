#!/usr/bin/env python
# Paul Sladen, BSD
# For Till...

import sys

class Token():
    def __init__(self, start, end, what, **kwargs):
        self.start = start
        self.end = end
        self.what = what
        self.__dict__.update(kwargs)
    def __repr__(self):
        return '%s(%d,%d,%s)\n' % (self.__class__.__name__, self.start, self.end, `self.what`)
    def __str__(self):
        return self.what

class Whitespace(Token):
    pass
class Regular(Token):
    pass
class Keyword(Token):
    pass
class String(Token):
    def __str__(self):
        return '(' + self.what + ')'
    pass
class Delimiter(Token):
    pass
class Name(Token):
    def __str__(self):
        return '/' + self.what
class HexString(String):
    def __str__(self):
        e = self.what.encode('hex')
        # full-circle auto zero append
        if self.__dict__.has_key('zero_append') and self.zero_append == True:
            assert e[-1] == '0'
            e = e[:-1]
        return '<' + self.what.encode('hex') + '>'
class Comment(Token):
    pass
class Stream(String):
    def __str__(self):
        return self.what
    pass

class Tokeniser():
    whitespace = '\x00\x09\x0a\x0c\x0d\x20'
    delimiters = '()<>[]{}/%'
    def go(self, text, start, end):
        self.found = []
        i = start
        last = i - 1
        while i < end:
            #print '...', `text[i]`, i
            assert last < i
            #if len(self.found) > 0: print self.found[-1]
            last = i
            if text[i] in self.whitespace:
                whitespace = ''
                j = i 
                while j < end and text[j] in self.whitespace:
                    whitespace += text[j]
                    j += 1
                # whitespace
                #print 'whitespace', i
                self.found.append(Whitespace(i, j, whitespace))
                i = j
                continue
            elif text[i] in self.delimiters:
                if text[i] == '(':
                    # string
                    string = ''
                    nested = 1
                    j = i+1
                    while nested > 0:
                        #print 'Chewing on', `text[i:i+50]`, `string`, `text[j:j+2]`
                        minimums = [text.index(')', j, end)]
                        try: minimums.append(text.index('\\', j, end))
                        except ValueError: pass
                        try: minimums.append(text.index('(', j, end))
                        except ValueError: pass
                        j = min(minimums)
                        string += text[i+1:j]
                        if text[j] in '()':
                            nested += [1, -1]['()'.index(text[j])]
                            if nested > 0:
                                string += text[j]
                            j += 1
                        elif text[j] == '\\':
                            #print 'Working on', `text[i:i+50]`, `string`
                            j += 1
                            if text[j] in 'nrtbf()\\':
                                # escapes
                                string += '\n\r\t\b\f()\\'['nrtbf()\\'.index(text[j])]
                                j += 1
                                i = j
                            elif text[j] in '\r\n':
                                # multi-line string escape
                                j += 1
                            elif text[j].isdigit():
                                octal = 0
                                # octal escapes
                                for k in xrange(j, j+3):
                                    if text[k].isdigit():
                                        octal = octal << 3 + int(text[k].isdigit(),10) & 7
                                    else:
                                        j = k
                                        break
                            else:
                                #assert not 'junking'
                                # junk 
                                pass
                    #print 'string', `string`
                    self.found.append(String(i, j, string))
                    i = j
                elif text[i] is '<':
                    if text[i+1] is '<':
                        # dictionary start
                        self.found.append(Delimiter(i, i+2, '<<'))
                        i += 2
                    else:
                        # hexstring
                        j = text.index('>', i, end)
                        print >>sys.stderr, `text[i+1:j]`
                        zero_append = (j - 1 - i) & 1
                        hexstring = (text[i+1:j] + '0' * zero_append).decode('hex')
                        self.found.append(HexString(i, j, hexstring, zero_append=zero_append))
                        i = j + 1
                elif text[i] is '>':
                    if text[i+1] is '>':
                        # dictionary end
                        self.found.append(Delimiter(i, i+2, '>>'))
                        i += 2
                elif text[i] in '[]':
                        # array
                        self.found.append(Delimiter(i, i+1, text[i]))
                        i += 1
                elif text[i] is '/':
                    # name
                    name = ''
                    j = i + 1
                    while j < end:
                        if text[j] in (self.whitespace + self.delimiters):
                            break
                        elif text[j] == '#':
                            name += int(text[j+1:j+1+2], 16)
                            j += 3
                        else:
                            name += text[j]
                            j += 1
                    self.found.append(Name(i, j, name))
                    i = j
                elif text[i] is '%':
                    j = text.index('\n', i+1, end)
                    self.found.append(Comment(i, j+1, text[i:j+1]))
                    i = j + 1
                else:
                    assert 'unhandled delimiter', `text[i]`
            else:
                # keyword
                keyword = ''
                j = i
                while j < end:
                    if text[j] in (self.whitespace + self.delimiters):
                        break
                    else:
                        keyword += text[j]
                        j += 1
                self.found.append(Keyword(i, j, keyword))
                i = j
                if keyword == 'stream':
                    # stream contents, \r follower not allowed
                    # currently this does not strip the newline off the front
                    assert text[i] == '\n' or text[i:i+2] == '\r\n'
                    extent = 1 + text.index('\n',i,i+2)
                    self.found.append(Whitespace(i, extent, text[i:extent]))
                    j = text.index('\nendstream', extent, end)
                    self.found.append(Stream(extent, j, text[extent:j]))
                    i = j
 
class impositor:
    def open(self, f):
        self.contents = f.read()
    def parse(self):
        self.t = Tokeniser()
        assert self.contents[0:5] == '%PDF-'
        self.pdf_version = float(self.contents[5:8])
        self.pdf_startxref = self.contents.rindex('startxref')
        self.pdf_xref_offset = int(self.contents[self.pdf_startxref + len('startxref'):-len('%%EOF\n')])
        #try:
        #    self.t.go(self.contents, self.pdf_xref_offset, self.pdf_startxref)
        #except AssertionError:
        #    pass
        self.t.go(self.contents, 0, len(self.contents))
        for f in self.t.found:
            sys.stdout.write(str(f))
        pass
    
def main():
    i = impositor()
    fp = open(sys.argv[1], 'r')
    i.open(fp)
    i.parse()

if __name__=='__main__':
    main()
