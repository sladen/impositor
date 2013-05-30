#!/usr/bin/env python
# Paul Sladen, BSD
# For Till...

import sys

class Token():
    def __init__(self, start, end, what):
        self.start = start
        self.end = end
        self.what = what
    def __repr__(self):
        return '%s(%d,%d,%s)\n' % (self.__class__.__name__, self.start, self.end, `self.what`)

class Whitespace(Token):
    pass
class Keyword(Token):
    pass
class String(Token):
    pass
class Delimiter(Token):
    pass
class Name(Token):
    pass
class HexString(String):
    pass

class Tokeniser():
    whitespace = '\x00\x09\x0a\x0c\x0d\x20'
    delimiters = '()<>[]{}/%'
    def go(self, text, start, end):
        self.found = []
        i = start
        while i < end:
            print '...', `text[i]`
            if text[i] in self.whitespace:
                whitespace = ''
                j = i 
                while j < end and text[j] in self.whitespace:
                    whitespace += text[j]
                    j += 1
                # whitespace
                print 'whitespace', i
                self.found.append(Whitespace(i, j, whitespace))
                i = j
                continue
            elif text[i] in self.delimiters:
                if text[i] == '(':
                    # string
                    string = ''
                    nested = 1
                    while nested > 1:
                        j = min(text.index(')', i+1, end), text.index('(', i+1, end), text.index('\\', i+1, end))
                        string += text[i+1:j]
                        if text[j] in '()':
                            string += text[j]
                            nested += [1, -1]['()'.index(text[j])]
                        elif text[j] == '\\':
                            j += 1
                            if text[j] in 'nrtbf()\\':
                                # escapes
                                string += '\n\r\t\b\f()\\'['nrtbf()\\'.index(text[j])]
                                j += 1
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
                                # junk 
                                pass
                    print 'string', `string`
                    self.found.append(String(start, end, string))
                    i = j
                elif text[i] is '<':
                    if text[i+1] is '<':
                        # dictionary start
                        self.found.append(Delimiter(i, i+2, '<<'))
                        i += 2
                    else:
                        # hexstring
                        j = text.index('>', i)
                        hexstring = (text[i+1:j-1] + '0' * ((j - i) & 1)).decode('hex')
                        self.found.append(HexString(i, j, hexstring))
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
 
class impositor:
    def open(self, f):
        self.contents = f.read()
    def parse(self):
        self.t = Tokeniser()
        assert self.contents[0:5] == '%PDF-'
        self.pdf_version = float(self.contents[5:8])
        self.pdf_startxref = self.contents.rindex('startxref')
        self.pdf_xref_offset = int(self.contents[self.pdf_startxref + len('startxref'):-len('%%EOF\n')])
        try:
            self.t.go(self.contents, self.pdf_xref_offset, self.pdf_startxref)
        except AssertionError:
            pass
        print self.t.found
            
    
def main():
    i = impositor()
    fp = open(sys.argv[1], 'r')
    i.open(fp)
    i.parse()

if __name__=='__main__':
    main()
