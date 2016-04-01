#!/bin/python

# Python program to calculate Easter date for a given year.
# This program was translated from an *ancient* BASIC program
# taken from a certain black papercover book course on BASIC
# programming whose title totally escapes me, as that was
# during my high school time. Obviously placed in public
# domain, and don't ask me how it works! :-)

print
i = int(raw_input('Year: '))
v = i % 19
w = i % 4
t = i % 7
c = 19*v+24
s = c % 30
c = 2*w+4*t+6*s+5
z = c % 7
d = 22+s+z
if d <= 31:
    print 'The date of Easter is March %d, %d' % (d,i)
else:
    d -= 31
    print 'The date of Easter is April %d, %d' % (d,i)
