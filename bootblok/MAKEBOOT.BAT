@echo off
rem ---- future: handles MBR case
if $%1==$ goto help
echo w cs:100 %2 0 1 >makeboot.cmd
echo q >>makeboot.cmd
debug %1 <makeboot.cmd
del makeboot.cmd
goto done

:help
echo.
echo MAKEBOOT {filename} {drive number}
echo.
echo where {filename} contains a boot image to be written to
echo the boot sector.  Only the first 512 bytes from this
echo file will be written.
echo.
echo {drive number} denotes which drive the boot code will be
echo placed on.  0 = A, 1 = B, etc. is the numbering scheme.
echo.
echo MAKEBOOT by itself gives help message.
echo.

:done
