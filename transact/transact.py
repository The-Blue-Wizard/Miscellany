#!/bin/python

# This Python script implements the algorithm to simulate
# a transformation of a fictional programming language
# based on C called Skeleton.

# The Skeleton grammar is dead simple -- it is made up of
# only these tokens (whitespaces are completely ignored,
# but will be preserved in the transformation), which
# are: func, stmt, flowstmt, goto, {, }, and maybe one
# more which escapes my mind.  Do note that if, while,
# and other such statements can be easily represented
# by the phrase flowstmt { ... }.  The grammar is just
# this:
#
#    program:
#        <empty>
#        program function-definition
#
#    function-definition:
#        "func" block
#
#    block:
#        "{" stmt-list "}"
#
#    stmt-list:
#        <empty>
#        stmt-list statement
#
#    statement:
#        "stmt"
#        "goto" label
#        "flowstmt" statement
#        block


# The T-Skeleton grammar is a superset of Skeleton by
# the straightforward addition of __check, __error,
# __success, __failure and __finally keywords, and
# appropriate new grammar rules.
#
# Note that here the syntax for '__check' is
#
#     __check label
#
# as there is no notion of expression in the T-Skeleton
# "language" ('label' is a purely dummy identifier).
# Moreover, it is automatically transformed into:
#
#    flowstmt /* !(label) */ goto __error
#
# and the 'label' will be ignored (actually, it will be
# converted into a comment, as shown in the transformed
# statement above.)

class Parser:
    EOF, OPENBRACE, CLOSEBRACE, WHITESPACE, STMT, \
        FLOWSTMT, IDENTIFIER, TRANSACT, COMMENT = range(9)

    def __init__(self,f):
        import re
        self._f = f
        self._linebuf = []
        self._delim = re.compile(r'([{}]|\n|\s+|/\*.*)',re.DOTALL)
        self.token = ''
        self.classifytoken()

    def close(self):
        # close the file and returns
        self._f.close()
        self._f = None
        self.token = None

    def _getline(self):
        if self._f == None:
            return ''
        l = self._f.readline()
        if l == '':
            self.close()
        return l

    def getsimpletoken(self):
        # note that it DOES return a string of whitespaces!
        # also, it does not fully process the comments, so
        # take care to deal with it when it comes up!

        while self._linebuf == []:
            l = self._getline()
            if l == '':
                return
            self._linebuf = self._delim.split(l)
        self.token = self._linebuf.pop(0)

    def classifytoken(self):

        # check for delimiters

        if self.token == None:
            self.tokentype = self.EOF
        elif self.token == '{':
            self.tokentype = self.OPENBRACE
        elif self.token == '}':
            self.tokentype = self.CLOSEBRACE

        # check for "usual" and flow stmts

        elif self.token == 'stmt':
            self.tokentype = self.STMT
        elif self.token == 'flowstmt':
            self.tokentype = self.FLOWSTMT

        # check for transact keywords

        elif self.token in ('__check', '__error',
            '__success', '__failure', '__finally'):
            self.tokentype = self.TRANSACT

        # check for other types

        elif self.token.strip() == '':
            self.tokentype = self.WHITESPACE
        elif self.token[:2] == '/*':
            self.tokentype = self.COMMENT
        else:
            self.tokentype = self.IDENTIFIER

    def gettoken(self):
        # find next nonempty token
        while 1:
            self.getsimpletoken()
            if self.token != '':
                break
        self.classifytoken()
        # deal with the COMMENT in a complete manner
        if self.tokentype == self.COMMENT:
            # process the comment
            i = self.token.find('*/',2)
            if i > -1:
                self._linebuf = self._delim.split(self.token[i+2:])
                self.token = self.token[:i+2]
                return
            while i == -1:
                l = self._getline()
                if l == '':
                    print 'End of file reached without comment terminator'
                    return
                i = l.find('*/')
                if i == -1:
                    self.token += l
            self._linebuf = self._delim.split(l[i+2:])
            self.token += l[:i+2]
        # end...all done!

    def match(self,tok):
        if self.token != tok:
            print "ERROR: Token '%s' expected, but encountered '%s' instead" % (tok, self.token)
            return 0
        self.gettoken()
        return 1

# The Writer implements an engine for intelligent formatted outputting
# (the current implementation is admittedly rather simple-minded ;)

class Writer:
    def __init__(self,f):
        self._f = f
        self._linebuf = ''
        self._indent = ''
        self._newline = 1

    def indentedwrite(self,txt):
        if self._newline and txt != '\n':
            self._f.write(self._indent)
        self._f.write(txt)
        self._newline = (txt == '\n')

    def write(self,txt):
        self._f.write(txt)
        if self._newline and txt.strip() == '':
            self._indent = txt
        self._newline = (txt == '\n')

    def close(self):
        self._f.write(self._linebuf)  # flush any remaining linebuf
        self._f.close()
        self._f = None

class InjectableParser(Parser):
    def __init__(self,f):
        Parser.__init__(self,f)
        self._inject = []

    def gettoken(self):
        if self._inject != []:
            self.token = self._inject.pop(0)
        else:
            Parser.gettoken(self)

    def inject(self,*tokenlist):
        # Note: the tokenlist must be a series of token strings
        self._inject += list(tokenlist)

#
# TranslatorParser is a specialized parser geared for use by
# the Translator class.  It processes __check statement and
# provides extra, transparent support for comment outputting.
#

class TranslatorParser(InjectableParser):

    def __init__(self,f):
        InjectableParser.__init__(self,f)

    def gettoken(self):
        InjectableParser.gettoken(self)
        if self.token == '__check':
            # translate it and then return the first token
            while 1:
                InjectableParser.gettoken(self)
                if self.tokentype in (self.WHITESPACE, self.COMMENT):
                    continue
                pseudoexpr = self.token
                break
            if self.tokentype == self.EOF:
                print 'Pseudoexpr expected, end of file encountered instead'
                return
            self.translate_check_stmt(pseudoexpr)

            # having translated it, simply get the token again
            # which will be the first of the translated tokens.
            InjectableParser.gettoken(self)

    def translate_check_stmt(self,pseudoexpr):
        self.inject('flowstmt', ' ', '/* !(%s) */' % (pseudoexpr,), \
            ' ', 'goto', ' ', '__error')

class Translator:
    FUNCTION, STATEMENT = 0, 1
    CHECK, ERROR, SUCCESS, FAILURE, FINALLY = [i**2 for i in range(5)]
    transact_map = { '__check': (CHECK, ''),      '__error': (ERROR, 'e'),
                     '__success': (SUCCESS, 's'), '__failure': (FAILURE, 'f'),
                     '__finally': (FINALLY, 'c') }

    def __init__(self,parser,writer):
        self._parser = parser
        self._writer = writer
        self._blocknesting = 0
        self._blocksection = 0
        self.reset()

    def reset(self):
        self._gototypeseen = 0
        self._transactstmtseen = 0

    def gettoken(self):
        # a yet more intelligent token getter...
        # this time it processes whitespaces and comments completely,
        # and thereby hides a bit more details :)
        p = self._parser  # get the current parser
        p.gettoken()
        # skip whitespaces and comments (and write them out too)
        while p.tokentype in (p.WHITESPACE, p.COMMENT):
            self._writer.write(p.token)
            p.gettoken()

    def match(self,tok):
        # make sure we skip whitespaces and comments (and write them out too)
        p = self._parser  # get the current parser
        while p.tokentype in (p.WHITESPACE, p.COMMENT):
            self._writer.write(p.token)
            p.gettoken()
        return p.match(tok)

    def make_label(self,labeltype,blockoffset=0,sectionoffset=0):
        return '_t%02d%02d%s' % (self._blocknesting+blockoffset,self._blocksection+sectionoffset,labeltype)

    def translate_flowstmt(self):
        while self._parser.token == 'flowstmt':
            self._writer.write('flowstmt')
            self.gettoken()
        self.translate_stmt()

    def translate_transact(self):
        # returns 1 if a transact is found, 0 otherwise
        tok = self._parser.token
        if self.transact_map.has_key(tok) == 0:
            return 0
        transactcode = self.transact_map[tok]
        if self._transactstmtseen & transactcode[0] != 0:
            print '%s transact already seen!  Output will be unreliable' % \
               (tok,)
        self._transactstmtseen |= transactcode[0]
        if transactcode[0] == self.ERROR:
            pass
        elif transactcode[0] == self.SUCCESS:
            pass
        elif transactcode[0] == self.FAILURE:
            pass
        elif transactcode[0] == self.FINALLY:
            pass
        return 1

    def section_coda(self):
        # this is called after a sequence of stmts followed by a
        # series of transacts are parsed.  This verifies the
        # usage of transact gotos and transact statements,
        # wraps up the stuff...
	
        # first, it checks to make sure that goto __error and
        # __error transact are either both present or both
        # absent, and issue an error message otherwise.
        # (so, rule #1 and #2 are met)
        if ((self._gototypeseen ^ self._transactstmtseen) & self.ERROR) != 0:
            if (self._gototypeseen & self.ERROR) != 0:
                print "ERROR:  Missing __error transact for goto __error"
            else:
                print "ERROR:  Missing goto __error for __error transact"
        # generate default transacts...
        if (self._transactstmtseen & self.SUCCESS) == 0:
            # generate <label> goto __finally
            self._writer.indentedwrite('%s: goto %s;\n' % (self.make_label('s'), self.make_label('c')))
        if (self._transactstmtseen & self.FAILURE) == 0:
            self._writer.indentedwrite('_tfailure = 1;\n')
            # generate <label> goto __finally
            self._writer.indentedwrite('%s: goto %s;\n' % (self.make_label('f'), self.make_label('c')))
        if (self._transactstmtseen & self.FINALLY) == 0:
            self._writer.indentedwrite('%s:\n' % (self.make_label('c'),))
            # generate the equiv. for goto __(prev)failure and goto __(prev)success, resp.
            self._writer.indentedwrite('    if (_tfailure) goto %s;\n' % (self.make_label('f',0,-1),))
            self._writer.indentedwrite('    else           goto %s;\n' % (self.make_label('s',0,-1),))
        self._writer.indentedwrite('%s:\n' % self.make_label('',0,1))

    def translate_others(self):
        pass

    def translate_stmt(self):
        # returns 1 if a stmt is found, 0 otherwise
        tok = self._parser.token
        if tok == 'stmt':
            self.match('stmt')
            self._writer.write('stmt')
        elif tok == 'flowstmt':
            self.translate_flowstmt()
        elif tok == '{':
            self.translate_block(self.STATEMENT)
        elif tok == 'goto':
            self.gettoken()
            tok = self._parser.token
            if self.transact_map.has_key(tok):
                self._gotostmtseen |= self.transact_map[tok][0]
                label = self.make_label(self.transact_map[tok][1],0,1)
                self._writer.indentedwrite('goto %s;\n' % (label,))
            else:
                print 'ERROR: Bad goto statement: "goto %s"' % (tok,)
        else:
            return 0
        return 1

    def translate_block(self,blocktype):
        self.match('{')
        self._writer.write('{')
        self._blocknesting += 1
        oldblocksection = self._blocksection
        self._blocksection = 0
        self.reset()
        if blocktype == self.FUNCTION:
            self._writer.indentedwrite('int __tfailure = 0;\n')
        # start processing sections...
        while self._parser.token != '}':
            while self.translate_stmt():
                pass
            while self.translate_transact():
                pass
            self.section_coda()
        # then...
        self.match('}')
        self._blocknesting -= 1
        self._blocksection = oldblocksection
        if blocktype == self.FUNCTION:
            self._writer.indentedwrite('_t0000:\n')
        self._writer.write('}')

    def translate_func(self):
        self.match('func')
        self._writer.write('func')
        self.translate_block(self.FUNCTION)
        # add some sanity check here?

    def translate(self):
        self.gettoken()
        while self._parser.token == 'func':
            self.translate_func()
        # verify that it has reached EOF...if not, error

if __name__ == '__main__':
    import sys
    fn = sys.argv[1]
    outfn = sys.argv[2]
    # to be continued
