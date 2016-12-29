# A GUI system (for Kestrel computers, and for others, perhaps...)

This is the very first draft.

Right now I am just listing a grab bag of various
ideas, and everyone is invited to contribute, comment, etc.

OK, the GUI system should be modular, lightweight, responsive

## Some GUIs we like...

What kc5tja likes:

* OS/2 2.0
* Amiga 2.04
* Win 95
* GEM 1.0 (with a bit of updates)

What TheBlueWizard likes:

* Amiga 2.04
* Win 95

## Desirable traits of GUI:

GUI should be customizable (something similar to MUI). The event flow as found in web browsers'
Document Object Model (DOM) should be emulated (sorear). kc5tja notes that the configurability
in GEM would be done by replacing AES.

TheBlueWizard likes the idea of layers (X Windows, win manager, etc.).

kc5tja likes the idea of layers too, but instead of a tall stack of layers, like this:

    App
    |
    v
    GTK
    |
    v
    GDK
    |
    v
    X11
    |
    v
    Device Driver
    |
    v
    Hardware

he prefers instead a wide, flattened hierarchy, much as the original GEM was architected:

    App
    |
    *---------*------/ /----.
    |         |             |
    V         V             V
    GEMDOS<->AES   (other components)
    |   ^                   :
    |   +- - - - - - / / - -'
    V
    VDI
    |
    V
    Hardware

The idea is that "other components" could include things not originally conceived when VDI/AES/GEMDOS were conceived.
TV tuner cards, MPEG accelerators, and so forth can be orthogonally added to the system.  At least in theory.
If the application plays nice (that is, obeys AES rules about which portions of the screen it owns),
it can even touch raw framebuffer hardware *directly* if it wants (though obviously not recommended).

kc5tja doesn't expect *the* original GEM architecture to be used in the final GUI.
However, it is a model to aspire to, as it strictly enforced separation of concerns.
VDI provided raw drawing primitives with best possible efficiency.
AES provided window management services.
GEMDOS multiplexed amongst a number of different VDI drivers, included support for loadable fonts, device independent coordinate systems, and preferences management.
Following a similar philosophy of strict separation of concerns, it should be possible to build an easily maintainable GUI environment.

Note that everything 
GUI should have internal communication protocol, like one widget get updated from
another widget, etc.

