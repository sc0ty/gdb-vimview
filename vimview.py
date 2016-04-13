# Copyright (c) 2016, Michal Szymaniak
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import gdb
import subprocess
import os.path


### Remote communication with vim ###
class VimRemote:
	serverName = None
	cmd = None
	debug = False

	curFile = None
	curLine = None

	nullPipe = None

	def __init__(self):
		self.nullPipe = open(os.devnull, 'w')
		self.setServerName('gdb')

	def dbgPrint(self, info, msg):
		if self.debug and msg:
			gdb.write('vimview ' + info + ': ' + msg + '\n')

	def setServerName(self, name):
		if name:
			self.serverName = name
			self.cmd = ['vim', '--servername', name]

	def execCmd(self, command):
		cmd = self.cmd + ['--remote-expr', command]
		self.dbgPrint('cmd', str(cmd))

		vim = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = vim.communicate()

		if out:
			out = out.decode('utf-8')
			self.dbgPrint('out', out)

		if err:
			err = err.decode('utf-8')
			self.dbgPrint('err', err)

		return out, err
	
	def openFile(self, fileName, lineNo=None, existingOnly=True, reopen=False):
		if not reopen and (fileName == self.curFile and lineNo == self.curLine):
			return False

		if existingOnly and not os.path.isfile(fileName):
			return False

		if lineNo:
			cmd = self.cmd + ['--remote', '+' + str(lineNo), fileName]
		else:
			cmd = self.cmd + ['--remote', fileName]

		self.dbgPrint('cmd', str(cmd))

		self.curFile = fileName
		self.curLine = lineNo

		subprocess.Popen(cmd, stdout=self.nullPipe, stderr=self.nullPipe)
		return True

	def openCurrentFile(self, showError=True, existingOnly=True, reopen=False):
		try:
			frameSym = gdb.selected_frame().find_sal()
			if not frameSym.is_valid():
				if showError:
					gdb.write('this is not a valid frame\n')
				return
		except gdb.error:
			if showError:
				gdb.write('no frame is selected\n')
			return

		if not frameSym.symtab:
			if showError:
				gdb.write('can\'t read symbol for current frame\n')
			return

		if not frameSym.symtab.filename:
			if showError:
				gdb.write('cant read filename for current frame\n')
			return

		file = frameSym.symtab.fullname()
		self.openFile(file, frameSym.line, existingOnly, reopen)

global vimRemote


### Command: view current file in vim ###
class CmdView(gdb.Command):
	def __init__(self, cmd):
		super (CmdView, self).__init__(cmd, gdb.COMMAND_USER)

	def invoke(self, arg, from_tty):
		global vimRemote
		vimRemote.openCurrentFile(showError=True, reopen=True)


### Command: set breakpoint under vim cursor ###
class CmdBreak(gdb.Command):
	def __init__(self, cmd):
		super(CmdBreak, self).__init__(cmd, gdb.COMMAND_USER)

	def invoke(self, arg, from_tty):
		global vimRemote
		out, err = vimRemote.execCmd('expand("%:p") . ":" . line(".")')
		fileName = out.rstrip()

		if not err:
			gdb.Breakpoint(fileName, gdb.BP_BREAKPOINT)
		else:
			gdb.write('error: ' + err.decode('utf-8'))


### Parameter: set vim server name ###
class SetServerName(gdb.Parameter):
	def __init__(self, cmd):
		self.set_doc = 'Vim server name:'
		self.show_doc = self.set_doc
		super(SetServerName, self).__init__(cmd, gdb.COMMAND_NONE, gdb.PARAM_STRING)

		global vimRemote
		self.value = vimRemote.serverName

	def get_set_string(self):
		global vimRemote
		vimRemote.setServerName(self.value)
		return self.value


### Event handlers ###
def eventStop(ev):
	global vimRemote
	vimRemote.openCurrentFile(showError=False, reopen=True)


### Prompt hook ###
def prompt(pr):
	global vimRemote
	vimRemote.openCurrentFile(showError=False)
	return None


if __name__ == "__main__":
	if 'vimRemote' not in globals():
		vimRemote = VimRemote()

	CmdView('vim')
	CmdView('v')
	CmdBreak('vbreak')
	SetServerName('vim-server')

	gdb.events.stop.connect(eventStop)
	gdb.prompt_hook = prompt

