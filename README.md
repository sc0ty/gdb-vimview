# GDB VimView
View current gdb frame in vim.
Vim will automatically open files and set cursor position according to gdb context.

## What is it
This is gdb plugin that will synchronize vim with gdb (running in separate terminal) to show you (with vim) the context of what is going on in gdb session. Vim will automatically update cursor position on break, step by step execution, backtrace examination, thread changes and many more.

## How does it work
Vim has the ability to run as server, executing remote commands. VimView is a Python plugin that exploit this feature.

## Requirements
1. Gdb with python support compiled in. Test with `python-interactive` command under gdb.
2. Vim/gvim with `clientserver` option compiled in. Test it with `vim --version` - look for `+clientserver`. Note that vim needs to be run under X11/XWindow to be able to communicate (even the terminal version).
You could try to run server:
```
vim --servername test
```
and remotely send command to it:
```
vim --servername test --remote ~/.vimrc
```

## Usage
To start, run vim in server mode:
```
vim --servername gdb
```
And (in another terminal) under gdb:
```
source /path/to/vimview.py
set vimview-onstop on
set vimview-onprompt on
```
You could also add this to your `.gdbinit`.

Now start debugging and you will see the magic.

### Commands
Gdb commands available:
 - `v` or `vim` - show current frame in vim
 - `vbreak` - set breakpoint under current vim cursor position
 - `vbreak [no]` - show breakpoint position in vim

### Configuration
Gdb settings available:
 - `set vimview-server [name]` - change vim server name to use, default is `gdb`
 - `set vimview-onstop [on/off/auto]` - show current position in vim whenever debugging stops; if sets to `auto` it will be activated only when `VIMSERVER` variable is set
 - `set vimview-onprompt [on/off/auto]` - show position on every prompt print (only when position was updated); if sets to `auto` it will be activated only when `VIMSERVER` variable is set; it could interfere with other plugins that tries to hook prompt

Environment variables:
 - `VIMSERVER` - sets the server name, it is read only when this plugin is sourced

Convenience variables (to be used with other commands, e.g `print $vw()`):
 - `$vw()` - word under vim cursor
 - `$ve()` - expression under vim cursor
 - `$vf()` - absolute vim file path
 - `$vl()` - vim cursor line number
 - `$vfl()` - vim file:line, equivalent to `$vf():$vl()`

Debug options:
 - `pi vimRemote.debug = True` - print vim commands beeing executed

### Known bugs
 - this plugin may interfere with other gdb plugins that tries to hook prompt

