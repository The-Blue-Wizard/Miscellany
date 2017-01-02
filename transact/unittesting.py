#!/bin/python

# Unit testing for transact.py

from transact import *

def parse_header(p,header=0):
    # p is a parser
    textlist = []
    while 1:
        p.gettoken()
        t = p.token
        if t == None:
            print 'End of file reached and template is not found!'
            return None
        if p.tokentype == p.WHITESPACE:
            continue
        if p.tokentype == p.COMMENT:
            t = t[2:-2].lstrip()  # remove /* and */, then leading spaces
            if t[:1] == '@':
                # doc comment found, extract it
                textlist.append(t[1:])
            continue
        break
    # return the text list without unit test comment header
    if header:
        return textlist[:1]
    else:
        return textlist[1:]

def unittest(testtype,infname,outfname,argv):
    if testtype == 'parser':
        #
        # test the Parser's ability to properly
        # tokenize the stream.
        #
        p = Parser(open(infname,'rt'))
        s = ''
        while 1:
            p.gettoken()
            t = p.token
            if t == None:
                break
            print repr(t)
            s += t
        # check for consistency
        open(outfname,'wt').write(s)
        if s == open(infname,'rt').read():
            print 'All working fine'
        else:
            print "Token stream doesn't match file!"

    elif testtype == 'writer':
        #
        # test the Writer's ability to output stuff
        # in properly indented format
        #
        p = Parser(open(infname,'rt'))
        replacements = [t.strip() for t in parse_header(p)]
        if replacements == None:
            return
        w = Writer(open(outfname,'wt'))
        while 1:
            t = p.token
            if t == None:
                break
            if t == '#':
                w.indentedwrite(replacements.pop(0))
            else:
                w.write(t)
            p.gettoken()
        w.close()

    elif testtype == 'injectableparser':
        #
        # test the injection of the stream
        #
        ip = InjectableParser(open(infname,'rt'))
        injections = [t.strip() for t in parse_header(ip)]
        if injections == None:
            return
        s = ''
        while 1:
            t = ip.token
            if t == None:
                break
            if t == '#':
                # inject some stuff
                try:
                    item = injections.pop(0)
                except:
                    print 'Ran out of inject text! Quitting...'
                    return
                ip.inject(item)
                print '"%s" got injected' % (item,)
                ip.gettoken()  # get a new (injected) token
                continue
            s += t
            ip.gettoken()
        open(outfname,'wt').write(s)

    elif testtype == 'translatorparser':
        #
        # test TranslatorParser's ability to
        # automatically translate __check
        # statements.
        #
        tp = TranslatorParser(open(infname,'rt'))
        s = ''
        while 1:
            tp.gettoken()
            t = tp.token
            if t == None:
                break
            print repr(t)
            s += t
        open(outfname,'wt').write(s)

    elif testtype == 'translator':
        #
        # test Translator's entire job
        # (the test files should be individually
        # tailored to test each area).
        #
        t = Translator(TranslatorParser(open(infname,'rt')),Writer(open(outfname,'wt')))
        t.translate()  # do the whole work

def do_unittesting(argv):
    p = Parser(open(argv[1]))
    header = parse_header(p,1)
    p.close()
    p = None
    if header != None and header != []:
        # get the unit test type from the header
        header = header[0].strip().split()
        header, unittesting = (header[:1]+['default'])[0], header[1:]
        print header
        outfname = argv[2]
        if outfname == None:
	    outfname = argv[1]+'.out'
        unittest(header,argv[1],argv[2],unittesting+argv[3:])
    else:
        print 'Unit testing comment header not found, quit!'

def debug_unittesting(argv):
    import pdb
    pdb.run('do_unittesting(%s)' % (repr(argv),))

if __name__ == '__main__':
    import sys
    argv = sys.argv[:]
    if len(argv) < 2:
        # el cheapo, self documenting help message
        print 'General command (under Windows using PY.BAT):'
        print "py unittesting '' [-debug] testN.tp testN.out {extras} (where N is a digit)"
        sys.exit(0)
    if argv[1] == '-debug':
        del argv[1]
        debug_unittesting(argv)
    else:
        do_unittesting(argv)
