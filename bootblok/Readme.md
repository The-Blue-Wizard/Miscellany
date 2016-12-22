# BOOTBLOK.ASM

I wrote this boot code in assembly language for my old OS project (I only got as far
as writing a simple OSLOADER.SYS to prove that everything worked beautifully, and
nothing more).

The coolest part of this boot code? It can detect and report any possible problem
found while booting and print it on the screen. A total of 4 possible error messages
have been encoded. I also deliberately made finding OSLOADER.SYS completely
relocatable within root directory, so I can slap replace it and not worry about
having it in "precise" place when booting.

I also include BOOTBLOK.COM and MAKEBOOT.BAT (MAKEBOOT.BAT is in public domain; also
be sure that the binary file name ends in .COM so MSDOS DEBUG command can load it
into memory properly) for convenience.

Have fun studying and playing with it!
