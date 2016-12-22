;
; TITLE:  E-OS 1.0 Boot Sector
;
; Created: 08/05/1997
; Completed: 07/24/1998 (don't ask why ;-)
; Updated: 12/21/2016 (more text added with "update:", GPL version
;                      bumped to 3, new email address)
; Author: John Rogers
;         luinnissar [at] yahoo.com
;
;   Copyright (C) 2001, 2016  John Rogers (luinnissar [at] yahoo.com)
;
;   This program is free software; you can redistribute it and/or modify
;   it under the terms of the GNU General Public License as published by
;   the Free Software Foundation; either version 3 of the License, or
;   (at your option) any later version.
;
;   This program is distributed in the hope that it will be useful,
;   but WITHOUT ANY WARRANTY; without even the implied warranty of
;   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;   GNU General Public License for more details.
;
;   You should have received a copy of the GNU General Public License
;   along with this program.  If not, see <http://www.gnu.org/licenses/>.
;
; This is the source code (in NASM assembly format) for the
; E-OS (and other emerging OSes) partition boot record.  It is based
; on Win95 boot code derived from the one found on:
;    http://lance.advantweb.com (update: original code no longer exists
;                                on this website)
;
; This source file is assembled with NASM 0.97 assembler (downloadable
; from the Internet, see http://www.erols.com/johnfine for the exact
; whereabout of the NASM assembler; update: one can get the latest
; from http://www.nasm.us, though this assembly code has not been
; tested with the latest version of NASM, but I doubt there would be
; any problem) using the command:
;        nasm -f bin bootblok.asm -o bootblok.bin
; It can also be assembled via the batch command N bootblok. (Note:
; The batch script N.BAT is not included, but one can easily
; create such a script)
;
; You will need to use some utility to write BOOTBLOK.BIN onto the
; boot sector to complete the step.  The batch command MAKEBOOT
; included with this program provides one such service.
;
; Note that this boot code is tested only on old PCs with BIOS; it
; has NOT been tested on new PCs with UEFI or possibly even "newer"
; BIOS! Use it at your own risk!
;
; According to one source, after loading the boot code at
; 0000:7C00, the BIOS sets DL to 00h if the boot code comes
; from a floppy disk, or to 80h if the boot code comes
; from a hard drive, and then jumps to 0000:7C00.  This
; boot code does not use such information, though.
;
; The loaded OSLOADER.SYS is allowed to only use the following call
; points, along with their hex offsets (note that these routines
; works in real mode only, and these numbers must be updated whenever
; this file get assembled):
;       print_quit        7cd3h    jump only
;       error             7cd0h    jump only - for quick debug purpose only
;       quit              7cd6h    jump only
;       findrootfile      7cedh
;       readcluster       7d10h
;       readsector        7d1ch
;       readlinearsector  7d22h
;       message           7d5bh
; It also may use the following information:
;   bp    = boot parameters and scratch area
;   ax    = starting cluster number of the OSLOADER.SYS
;           (the first cluster is already read in)
;   es:bx = pointing to area just after the first cluster of
;           the OSLOADER.SYS is read in.
;   cx    = 0
;   on stack: INT 1E vector recovery data
;
; Any comments, flames, etc. are welcome!
;

    org  7c00h

%define cluster2startl  bp-04
%define cluster2starth  bp-02

    jmp  short start ; go to bootup code
    nop
;
; This is the boot disk partition info.
; Each data has an offset byte in parentheses and a description.
;
    db   "E-OS 1.0"  ;(03) system identifier
    dw   0200h       ;(0b) #bytes/sector    = 512
    db   01h         ;(0d) #sectors/cluster = 1
    dw   0001h       ;(0e) #reserved sector = 1
    db   02h         ;(10) #FATs            = 2
    dw   00e0h       ;(11) #files in root dir = 224
    dw   0b40h       ;(13) #sectors/disk(floppy) = 0b40h = 2880 sectors
    db   0f0h        ;(15) media type code:
                     ;   F0h = 5.25" - 1.2M, or 3.5" - 1.44M or 2.88 format
                     ;   F8h = hard drive
                     ;   F9h = 5.25" - 1.2M, or 3.5" - 720K
                     ;   FAh = 5.25" - 320K single-sided
                     ;   FBh = 3.5"  - 640K
                     ;   FCh = 5.25" - 180K
                     ;   FDh = 360K or 8"
                     ;   FEh = 5.25" - 160K
                     ;   FFh = 5.25" - 320K double-sided
    dw   0009h       ;(16) #sectors/FAT      = 0009h
    dw   0012h       ;(18) #sectors/track    = 0012h = 18
    dw   0002h       ;(1a) #R/W heads        = 0002h
    dw   0000h
    dw   0000h       ;(1c) #hidden sectors   = 00000000h
    dw   0000h
    dw   0000h       ;(20) #sectors/disk(hard) = 00000000h
    db   00h         ;(24) drive #: 00h (floppy) or 80h (hard drive)
    db   00h         ;(25) holds the R/W head to read from
    db   29h         ;(26) extended boot signature: 29h means MSDOS 4.0 or
                     ;    later (I am thinking about changing this signature)
    dw   15e2h
    dw   2e28h       ;(27) volume serial # (double)
    db   "E-OS       " ;(2b) volume label
    db   "FAT12   "  ;(36) file system type
    dw   loaderfile  ;(3e) filename string pointer for findrootfile
;
; disable interrupts and set up ss, sp, es
;
; CODE VALIDATED
;
start:
    cli
    xor  cx,cx
    mov  ss,cx
    mov  sp,7b80h    ; set up the stackbase
    push ss
    pop  es          ; cx=ss=es=0
;
; copy ROM BIOS disk table to working disk table
;
; CODE VALIDATED
;
    mov  bp,0078h    ; bp -> INT 1E vector
    lds  si,[bp+00h]
    push ds          ; save pointers in case of failure
    push si
    push ss
    push bx
    mov  di,7b90h    ; di -> new disk param block (dpb)
    mov  [bp+00h],di ; set new INT 1E vector at 0:7b90
    mov  [bp+02h],cx
    mov  cl,0bh      ; copy 11 bytes from ds:si (old INT 1E vector) to 0:7b90
    cld
    repz movsb
    push es
    pop  ds          ; ds=es=ss=0
;
; plug in some new values
;
; CODE VALIDATED
;
    mov  bp,7c00h    ; bp -> beginning of boot code
    mov  byte [di-02h],0fh ; plug settle time in new dpb
    mov  ax,[bp+18h] ; ax = sectors per track
    mov  [di-07h],al ; plug in new dpb
    sti              ; must enable int for BIOS call
    cmp  [bp+24h],ah ; is it a hard drive?
    jl   skipint     ; yes
    mov  byte [replacemsg-1],0ffh ; plug in offset for "replace"
    int  13h         ; BIOS disk service function 0
    jb   error       ; goto error if it fails
skipint:
;
; calculate root directory and cluster 2 starting sector
;
; CODE VALIDATED
;
    mov  al,[bp+10h] ; al = #FATs on disk
    cbw              ; convert to word (al -> ax)
    mul  word [bp+16h] ; times sectors per FAT
    add  ax,[bp+1ch] ; add in hidden sectors (located past FATs, I think)
    adc  dx,[bp+1eh]
    add  ax,[bp+0eh] ; add in reserved sectors (this includes boot sector)
    adc  dx,cx       ;   cx still zero
    push ax          ; save dx:ax (root directory sector)
    push dx
    mov  [cluster2startl],ax ; save first part of cluster 2 calculation
    mov  [cluster2starth],dx
    mov  ax,0020h    ; ax = 32, directory entry size
    mov  si,[bp+11h] ; si = root directory entries
    mul  si          ; ax:dx = root directory bytes
    mov  bx,[bp+0bh] ; bx = bytes per sector
    add  ax,bx       ; ax += bytes per sector
    dec  ax          ; --ax
    div  bx          ; ax /= bytes per sector ->
                     ;    ax = quotient = sectors in root dir,
                     ;    dx = remainder = junk
    add  [cluster2startl],ax ; finish up cluster 2 calculation
    adc  [cluster2starth],cx ;    add carry (cx still zero)
    pop  dx
    pop  ax
;
; read the root directory and search it for OSLOADER.SYS
; if not found, report error
;
    call findrootfile ; find it
    jb   error       ; I/O error
    jz   cantfind    ; can't find it, report...
;
; load in the first cluster of the OSLOADER.SYS file at 7e00 and jump to it
;
    mov  bx,7e00h    ; starting address for file to be read in
    mov  cl,[bp+0dh] ; cx = one cluster to read in
    push ax          ; save cluster number
    call readcluster
    pop  ax          ; recover cluster number
    jb   error       ; loading fails
    jmp  0000h:7e00h ; jump to OSLOADER.SYS
;
; Routine: Error message printing and rebooting
; Entry points: cantfind and error
; Input:  None
; Output: Reboot!
; Error: None
;
; CODE VALIDATED
;
cantfind:
    mov  byte [cantfindmsg-1],0ffh ; set message to "Can't find ..."
error:
    mov  si,BOOThead
print_quit:
    call message     ; print messages
quit:
    xor  ax,ax       ; function 0 - read a keystroke
    int  16h
    pop  si          ; restore INT 1E pointer
    pop  ds
    pop  word [si]
    pop  word [si+02h]
    int  19h         ; and reboot!
;
;------------------ Subroutines -------------------
;
; Subroutine: Find a root file
; Entry point: findrootfile
; Input:  ax:dx = root dir starting sector
;         si = number of root dir entries (preloaded from [bp+11]
; Output: ax = its starting cluster number
; Error:  Carry flag set if I/O error occurred, cleared otherwise
;         Zero flag set if root file can not be found
;         Note: Root file is found if and only if both carry and
;               zero flags are both cleared
;
; CODE VALIDATED
;
findnext:
    dec  si
    jz   frf_done    ; no more entries...fails
    add  di,byte 15h ; (I'd like NASM to be optimizing, but...)
    cmp  di,bx       ; compare to end of buffer
    jb   findloop    ; still inside of it
findrootfile:
    mov  bx,0700h    ; bx -> buffer
    mov  di,bx       ; and so does di
    mov  cx,0001h    ; read one sector
    call readlinearsector
    jb   frf_error   ; failure
findloop:
    cmp  [di],ch     ; last entry?
    jz   frf_done    ; yes
    mov  cl,0bh      ; 11 bytes
    push si          ; save si (root dir entries)
    mov  si,[bp+3eh] ; si -> filename to compare against
    repz cmpsb       ; compare bytes
    pop  si
    jne  findnext    ; didn't match
    mov  ax,[di+0fh] ; get its cluster number
    or   ax,ax       ; set or clear zero flag accordingly
frf_done:
    clc
frf_error:
    ret
;
; Subroutine: read a cluster
; Input:  ax = cluster
;         cx = number of sectors to read in
;         es:bx = buffer to be filled in
; Output: buffer is filled in
; Error:  Carry set if I/O error, cleared otherwise
;
; CODE VALIDATED
;
readcluster:
    sub  ax,0002h    ; cluster -= 2
    jb   read_error  ; below 2...error
    xor  dx,dx       ; dx zeroed
    mov  dl,[bp+0dh] ; dx = sectors per cluster
    mul  dx          ; obtain a logical sector
;
; ----- and falls thru to... -----
;
; Subroutine: read a logical sector
; Input:  ax = logical sector low
;         dx = logical sector high
;         cx = number of sectors to read in
;         es:bx = buffer to be filled in
; Output: buffer is filled in
; Error:  Carry set if I/O error, cleared otherwise
;
; CODE VALIDATED
;
readsector:
    add  ax,[cluster2startl] ; dx:ax += cluster2start
    adc  dx,[cluster2starth]
;
; ----- and falls thru to... -----
;
; Subroutine: read a linear sector
; Input:  ax = linear sector low
;         dx = linear sector high
;         cx = number of sectors to read in
;         es:bx = buffer to be filled in
; Output: buffer is filled in
; Error:  Carry set if I/O error, cleared otherwise
;
; CODE VALIDATED
;
readlinearsector:
    push ax          ; ax = sector low
    push dx          ; dx = sector high
    push cx          ; cx = number of sectors
    xchg cx,ax       ; cx now = sector low
    xchg dx,ax       ; ax now = sector high
    xor  dx,dx       ; dx now zero
    div  word [bp+18h] ; dx:ax /= sectors per track
    xchg cx,ax
    div  word [bp+18h] ; dx:ax /= sectors per track ->
                     ;  ax = quotient = track,
                     ;  dx = remainder = sector
    inc  dx
    xchg cx,dx
    div  word [bp+1ah] ; dx:ax /= heads ->
                     ;  ax = quotient = cylinder,
                     ;  dx = remainder = head
    mov  dh,dl       ; dh = head number
    mov  dl,[bp+24h] ; dl = drive
    mov  ch,al       ; ch = low bits of cylinder
    ror  ah,1        ; cl = high bits of cylinder
    ror  ah,1
    or   cl,ah
    mov  ax,0201h    ; function 2, read one sector
    int  13h
    pop  cx          ; restore...
    pop  dx
    pop  ax
    jb   read_error  ; failure
    inc  ax          ; increase dx:ax by one
    jnz  skipinc
    inc  dx
skipinc:
    add  bx,[bp+0bh] ; bx -> next location in buffer (bx += bytes per sector)
    loop readlinearsector ; loop for each sector
read_error:
msg_exit:
    ret
;
; Subroutine: Print a message
; Entry point: message
; Input:  si -> pointer to message
; Output: message outputted
; Error:  None
;
; nextmsg: Given a chain number in al, start printing
; Input:  al = BYTE(-(offset+1))
;         si pointing to current text string
; Output: new si pointing to a new text string
;
; CODE VALIDATED
;
nextmsg:
    cbw              ; turn 80h+x into a negative offset,
    inc  ax          ; increase by one so it can have an offset of zero,
    sub  si,ax       ; and do a devious way to move pointer forward!
message:
    lodsb            ; subroutine #1: write character string
    or   al,al       ;   at ds:si to screen
    jz   msg_exit    ; string is zero-terminated
    js   nextmsg     ; negative, so do offset moving
    mov  ah,0eh      ; write char function
    mov  bx,0007h    ; page 0, color dim white
    int  10h         ; call BIOS
    jmp  short message ; loop back to write another character
;
; message area
;
; Chained messaging encoding scheme:
; A string of messages is encoded as a series of text strings
; ending in either a sentinel of zero or a BYTE(-(offset+1))
; (which would have a high bit set), pointing to next message
; segment.  A big advantage is that the pointing byte can be
; dynamically modified.  Offset is a non-negative number, thus
; it points to a message fragment further in the list.
;
; All such offsets are written down in decimal in parentheses.
;
; DATA VALIDATED
;
%define nl 0dh,0ah
%define linkto(l) db $-l
%define linktonext

messagestart:
BOOThead:
    db   nl,nl,"BOOT: "
    linkto(ioerrormsg) ; to either cantfindmsg or ioerrormsg (default)

cantfindmsg:
    db   "Could not find OSLOADER.SYS"
    linkto(pleasemsg)  ; to pleasemsg (constant)

ioerrormsg:
    db   "I/O error while reading disk"
    linktonext

pleasemsg:
    db   nl,nl,"Please "
    linkto(insertmsg)  ; to either replace or insert (default)

replacemsg:
    db   "replace"
    linkto(ask4diskmsg) ; to ask4diskmsg (constant)

insertmsg:
    db   "insert"
    linktonext

ask4diskmsg:
    db   " the disk and press any key when ready",nl,07h,00h

loaderfile:
    db   "OSLOADERSYS"

; ----may need some padding here----
    db   00

; boot block signature
    db   55h,0aah

; finito!
