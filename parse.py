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
    def dump_editor_utf8(self):
        return str(self).decode('latin-1').encode('utf-8').replace('\0','\\0')
    def dump_editor_utf8_with_tags(self):
        return [(self.dump_editor_utf8(), [])]

class Whitespace(Token):
    def dump_editor_utf8_with_tags(self):
        return [(self.dump_editor_utf8(), ['whitespace'])]
    pass
class Regular(Token):
    pass
class Keyword(Token):
    def dump_editor_utf8_with_tags(self):
        return [(self.dump_editor_utf8(), ['keyword'])]
    pass
class Number(Keyword):
    def dump_editor_utf8_with_tags(self):
        return [(self.dump_editor_utf8(), ['number'])]
    pass
class String(Token):
    def __str__(self):
        # less used
        return '(' + ''.join([str(x) for x in self.sub_strings]) + ')'
    def dump_editor_utf8(self):
        #print >>sys.stderr,`self.what[0:2]`
        if self.what.startswith('\xfe\xff'):
            return '(' + self.what.decode('utf-16').encode('utf-8') + ')'
        else:
            return self.__str__().decode('latin-1').encode('utf-8')
    def dump_editor_utf8_with_tags(self):
        try:
            #s = ''.join([str(x) for x in self.sub_strings])
            if self.what.startswith('\xfe\xff'):
                r = [('(' + self.what.decode('utf-16').encode('utf-8') + ')', ('string',))]
                return r
        except AttributeError: pass
        try:
            r = [('(', ('string',))]
            for x in self.sub_strings:
                r += x.dump_editor_utf8_with_tags()
            r += [(')', ('string',))]
        except AttributeError:
            r = [(self.dump_editor_utf8(), ['string'])]
        #print `r`
        return r
    pass
class Delimiter(Token):
    pass
class DelimiterOperator(Delimiter):
    def dump_editor_utf8_with_tags(self):
        return [(self.dump_editor_utf8(), ['operator'])]
    pass
class Name(Token):
    def __str__(self):
        return '/' + self.what
    def dump_editor_utf8_with_tags(self):
        return [(self.dump_editor_utf8(), ['name'])]
class HexString(String):
    def __str__(self):
        e = self.what.encode('hex')
        # full-circle auto zero append
        if self.__dict__.has_key('zero_append') and self.zero_append == True:
            assert e[-1] == '0'
            e = e[:-1]
        return '<' + self.what.encode('hex') + '>'
class Comment(Token):
    def dump_editor_utf8_with_tags(self):
        return [(self.dump_editor_utf8(), ['comment'])]
    pass
class Stream(String):
    def __str__(self):
        return self.what
    def dump_editor_utf8(self):
        return '<%d bytes>' % (self.end-self.start)
    def dump_editor_utf8_with_tags(self):
        return [(self.dump_editor_utf8(), ['stream'])]
    pass
class SubString(String):
    #def __str__(self):
    #    return '(' + ''.join([str(x) for x in self.sub_strings]).replace('\0','\\0') + ')'
    def __str__(self):
        return self.what
    def dump_editor_utf8(self):
        return str(self).replace('\0','\\0').decode('latin-1').encode('utf-8')
    def dump_editor_utf8_with_tags(self):
        return [(self.dump_editor_utf8(), ['substring'])]
class SubStringEscape(SubString):
    def __str__(self):
        return '\\' + self.what
    def dump_editor_utf8_with_tags(self):
        return [(self.dump_editor_utf8(), ['stringescape'])]
    pass
class SubStringEscapeOctal(SubStringEscape):
    def __str__(self):
        return '\\' + oct(ord(self.what))
class SubStringNested(String):
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
                    sub_strings = []
                    nested = 1
                    j = i+1
                    while nested > 0:
                        #print 'Chewing on', `text[i:i+50]`, `string`, `text[j:j+2]`
                        minimums = [text.index(')', j, end)]
                        try: minimums.append(text.index('\\', j, end))
                        except ValueError: pass
                        try: minimums.append(text.index('(', j, end))
                        except ValueError: pass
                        j2 = min(minimums)
                        sub_strings.append(SubString(j,j2,text[j:j2]))
                        j = j2
                        if text[j] in '()':
                            nested += [1, -1]['()'.index(text[j])]
                            if nested > 0:
                                sub_strings.append(SubStringNested(j, j+1, text[j]))
                            j += 1
                        elif text[j] == '\\':
                            #print 'Working on', `text[i:i+50]`, `string`
                            j += 1
                            if text[j] in 'nrtbf()\\':
                                # escapes
                                sub_strings.append(SubStringEscape(j-1, j+1, '\n\r\t\b\f()\\'['nrtbf()\\'.index(text[j])]))
                                j += 1
                                i = j
                            elif text[j] in '\r\n':
                                # multi-line string escape
                                j += 1
                            elif text[j].isdigit():
                                octal = 0
                                # octal escapes
                                for k in xrange(j, j+3):
                                    # 8 and 9 should be rounded to 7
                                    if text[k].isdigit():
                                        octal = octal << 3 + int(text[k],10) & 7
                                    else:
                                        break
                                sub_strings.append(SubStringEscapeOctal(j - 1, k, chr(octal), digits=k-j))
                                j = k
                            else:
                                #assert not 'junking'
                                # junk 
                                pass
                    #print 'string', `string`
                    #print >>sys.stderr, `sub_strings`
                    self.found.append(String(i, j, ''.join([x.what for x in sub_strings]), sub_strings=sub_strings))
                    i = j
                elif text[i] is '<':
                    if text[i+1] is '<':
                        # dictionary start
                        self.found.append(DelimiterOperator(i, i+2, '<<'))
                        i += 2
                    else:
                        # hexstring
                        j = text.index('>', i, end)
                        #print >>sys.stderr, `text[i+1:j]`
                        zero_append = (j - 1 - i) & 1
                        hexstring = (text[i+1:j] + '0' * zero_append).decode('hex')
                        self.found.append(HexString(i, j, hexstring, zero_append=zero_append))
                        i = j + 1
                elif text[i] is '>':
                    if text[i+1] is '>':
                        # dictionary end
                        self.found.append(DelimiterOperator(i, i+2, '>>'))
                        i += 2
                elif text[i] in '[]':
                        # array
                        self.found.append(DelimiterOperator(i, i+1, text[i]))
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
                    try:
                        j = text.index('\n', i+1, end)
                    except ValueError:
                        """testcase: http://www.thetram.net/pdfs/phase2Map/lenton/Gregory%20Street%20&%20Lenton%20Lane.pdf
                        which ends %%EOF\r"""
                        j = text.index('\r', i+1, end)
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
                try:
                    n = float(keyword)
                    self.found.append(Number(i, j, keyword))
                except:
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
        assert self.contents[0:5] in ('%PDF-', '%FDF-')
        self.pdf_version = float(self.contents[5:8])
        try:
            # FDF forms don't have a 'startxref'
            self.pdf_startxref = self.contents.rindex('startxref')
            self.pdf_xref_offset = int(self.contents[self.pdf_startxref + len('startxref'):-len('%%EOF\n')])
        except: pass
        #try:
        #    self.t.go(self.contents, self.pdf_xref_offset, self.pdf_startxref)
        #except AssertionError:
        #    pass
        self.t.go(self.contents, 0, len(self.contents))
        #for f in self.t.found:
        #    sys.stdout.write(str(f))

        if True:
            print >>sys.stderr, ' '.join(sys.argv)
            import pygtk
            pygtk.require('2.0')
            import gtk
            import pango
            w = gtk.Window(gtk.WINDOW_TOPLEVEL)
            w.set_title(' '.join(sys.argv))
            w.set_default_size(1000,600)
            icon = w.render_icon(gtk.STOCK_FIND_AND_REPLACE, gtk.ICON_SIZE_DIALOG)
            w.set_icon(icon)
            w.connect("destroy", lambda w: gtk.main_quit())
            ttt = gtk.TextTagTable()
            tb = gtk.TextBuffer(ttt)
            tv = gtk.TextView(tb)
            tv.set_wrap_mode(gtk.WRAP_NONE)
            #tv.set_editable(False)
            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
            sw.add(tv)
            h = gtk.HBox()
            h.pack_start(sw, True, True, 0)
            w.add(h)

            # Syntax highlighting colours picked to match
            # http://en.wikipedia.org/wiki/Syntax_highlighting example
            tt = gtk.TextTag('default')
            tt.set_property('family', 'monospace')
            #tt.set_property('background', '#c0c000')
            ttt.add(tt)

            tt = gtk.TextTag('monospace')
            tt.set_property('family', 'monospace')
            ttt.add(tt)

            tt = gtk.TextTag('comment')
            tt.set_property('foreground', '#808080')
            tt.set_property('style', pango.STYLE_ITALIC)
            ttt.add(tt)

            tt = gtk.TextTag('name')
            tt.set_property('foreground', '#993333')
            ttt.add(tt)

            tt = gtk.TextTag('keyword')
            tt.set_property('foreground', '#b1b100')
            ttt.add(tt)

            tt = gtk.TextTag('operator')
            tt.set_property('foreground', '#009900')
            ttt.add(tt)

            tt = gtk.TextTag('stream')
            tt.set_property('foreground', '#009900')
            ttt.add(tt)

            tt = gtk.TextTag('string')
            tt.set_property('foreground', '#ff0000')
            ttt.add(tt)

            tt = gtk.TextTag('substring')
            tt.set_property('foreground', '#ff0000')
            ttt.add(tt)

            tt = gtk.TextTag('stringescape')
            tt.set_property('foreground', '#000099')
            tt.set_property('weight', pango.WEIGHT_BOLD)
            ttt.add(tt)

            tt = gtk.TextTag('number')
            tt.set_property('foreground', '#0000dd')
            ttt.add(tt)

            tt = gtk.TextTag('whitespace')
            tt.set_property('background', '#f7f7f7')
            ttt.add(tt)

            start_iter, end_iter = tb.get_bounds()
            tb.apply_tag_by_name('default', start_iter, end_iter)
            for x in self.t.found:
                for text, tags in x.dump_editor_utf8_with_tags():
                    tb.insert_with_tags_by_name(start_iter, text, 'monospace', *tags)
            w.show_all()
            gtk.main()

    
def main():
    i = impositor()
    fp = open(sys.argv[1], 'r')
    i.open(fp)
    i.parse()

if __name__=='__main__':
    main()
