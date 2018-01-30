# Example .gdbinit

# it should be absolute path
source vimview.py

# show current position whenever debugging stops
set vimview-onstop on

# show position on every prompt print
set vimview-onprompt on

# set vim server name (case insensitive)
#set vimview-server myname

# open files in tabs
set vimview-tabs on

# enable debug mode
#pi vimView.debug = True

# glboal-symbol is used to find the location of source file when a new objectfile is loaded
#set vimview-global-symbol main

# show source file in Vim as soon as an object file is loaded in GDB
set vimview-new-objectfile on

# show/hide breakpoint markers in Vim
set vimview-new-breakpoint on
set vimview-delete-breakpoint on
