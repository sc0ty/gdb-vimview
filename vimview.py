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


### Helper functions ###

def _gdbBooleanToStr(val):
	if val == True:
		return 'on'
	elif val == False:
		return 'off'
	elif val == None:
		return 'auto'
	else:
		return str(val)

def _getVimServerNameVariable():
	return os.environ['VIMSERVER']

def _isVimServerNameVariableSet():
	try:
		_getVimServerNameVariable()
		return True
	except KeyError:
		return False


### Remote communication with vim ###
class VimView(object):
	def __init__(self):
		self.serverName = None
		self.binaryName = None

		self.cmd = None
		self.cmdFileArg = None
		self.debug = False

		self.curFile = None
		self.curLine = None

		self.nullPipe = open(os.devnull, 'w')
		self.setCommand(serverName='gdb', binaryName='vim', useTabs=False)

	def __del__(self):
		self.nullPipe.close()

	def dbgPrint(self, info, msg):
		if self.debug and msg:
			gdb.write('vimview ' + info + ': ' + msg + '\n')

	def setCommand(self, serverName=None, binaryName=None, useTabs=None):
		if serverName:
			self.serverName = serverName
		if binaryName:
			self.binaryName = binaryName
		if useTabs == True:
			self.cmdFileArg = '--remote-tab'
		elif useTabs == False:
			self.cmdFileArg = '--remote'

		self.cmd = [self.binaryName, '+q', '--servername', self.serverName]

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
			cmd = self.cmd + [self.cmdFileArg, '+' + str(lineNo), fileName]
		else:
			cmd = self.cmd + [self.cmdFileArg, fileName]

		self.dbgPrint('cmd', str(cmd))

		self.curFile = fileName
		self.curLine = lineNo

		vim = subprocess.Popen(cmd, stdout=self.nullPipe, stderr=self.nullPipe)
		vim.communicate()
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


### Command: view current file in vim ###
class CmdView(gdb.Command):
	"""Show current stack frame in vim.
This is part of the VimView plugin."""
	def __init__(self, cmd):
		super (CmdView, self).__init__(cmd, gdb.COMMAND_USER)

	def invoke(self, arg, from_tty):
		global vimView
		vimView.openCurrentFile(showError=True, reopen=True)


### Command: set breakpoint under vim cursor ###
class CmdBreak(gdb.Command):
	"""Set breakpoint under current vim cursor position.
If run with breakpoint number as argument, will show breakpoint position in vim.
This is part of the VimView plugin."""
	def __init__(self, cmd):
		super(CmdBreak, self).__init__(cmd, gdb.COMMAND_USER)

	def invoke(self, arg, from_tty):
		if arg:
			try:
				self.showBreak(int(arg))
			except ValueError:
				gdb.write('expected breakpoint number, got "' + arg + '"\n')
		else:
			self.putBreak()

	def putBreak(self):
		global vimView
		out, err = vimView.execCmd('expand("%:p") . ":" . line(".")')
		fileName = out.rstrip()

		if not err:
			try:
				gdb.Breakpoint(fileName, gdb.BP_BREAKPOINT)
			except RuntimeError as ex:
				gdb.write(str(ex) + '\n')
		else:
			gdb.write('error: ' + err)

	def showBreak(self, no):
		# TODO: handle non-file name locations
		global vimView
		try:
			br = next(x for x in gdb.breakpoints() if x.number==no)
			try:
				fileName, lineNo = br.location.rsplit(':', 1)
				lineNo = int(lineNo)
			except ValueError:
				fileName = br.location
				lineNo = None

			if not vimView.openFile(fileName, lineNo, reopen=True):
				gdb.write('cannot open file "' + fileName + '"\n')

		except StopIteration:
			gdb.write('no breakpoint number ' + str(no) + '\n')


### Convenience variable: word under vim cursor ###
class VarCursorWord(gdb.Function):
	cmd = None

	def __init__ (self, name, cmd):
		super(VarCursorWord, self).__init__ (name)
		self.name = name
		self.cmd = cmd

	def invoke(self, *args):
		global vimView
		out, err = vimView.execCmd(self.cmd)
		if not err:
			return out.rstrip()
		else:
			gdb.write('error: ' + err)
			return ''


### Event handlers ###
def eventStop(ev):
	global vimView
	vimView.openCurrentFile(showError=False, reopen=True)


### Prompt hook ###
def prompt(pr):
	global vimView
	vimView.openCurrentFile(showError=False)
	return None


### Parameter: vimview stop hook ###
class ParamVimViewOnStop(gdb.Parameter):
	"""This is part of the VimView plugin."""
	isHooked = False

	def __init__(self, cmd):
		super(ParamVimViewOnStop, self).__init__(cmd, gdb.COMMAND_SUPPORT, gdb.PARAM_AUTO_BOOLEAN)
		self.value = False
		self.set_doc = 'VimView: following frame on stop.'
		self.show_doc = self.set_doc

	def get_set_string(self):
		if self.value == None:	# auto
			self.value = _isVimServerNameVariableSet()

		if self.value:
			if not self.isHooked:
				gdb.events.stop.connect(eventStop)
				self.isHooked = True
		else:
			if self.isHooked:
				gdb.events.stop.disconnect(eventStop)
				self.isHooked = False
		return self.get_show_string(self.value)

	def get_show_string(self, svalue):
		return 'Vim follows frame on stop: ' + _gdbBooleanToStr(svalue)


### Parameter: vimview prompt hook ###
class ParamVimViewOnPrompt(gdb.Parameter):
	"""This is part of the VimView plugin."""
	prevHook = gdb.prompt_hook

	def __init__(self, cmd):
		super(ParamVimViewOnPrompt, self).__init__(cmd, gdb.COMMAND_SUPPORT, gdb.PARAM_AUTO_BOOLEAN)
		self.value = False
		self.set_doc = 'VimView: following frame on prompt show.'
		self.show_doc = self.set_doc

	def get_set_string(self):
		if self.value == None:	# auto
			self.value = _isVimServerNameVariableSet()

		if self.value:
			if gdb.prompt_hook != prompt:
				self.prevHook = gdb.prompt_hook
				gdb.prompt_hook = prompt
		else:
			gdb.prompt_hook = self.prevHook

		return self.get_show_string(self.value)

	def get_show_string(self, svalue):
		return 'Vim follows frame on prompt: ' + _gdbBooleanToStr(svalue)


### Parameter: vim server name ###
class ParamServerName(gdb.Parameter):
	"""This is part of the VimView plugin."""
	def __init__(self, cmd):
		super(ParamServerName, self).__init__(cmd, gdb.COMMAND_SUPPORT, gdb.PARAM_STRING)
		self.set_doc = 'VimView: remote vim server name.'
		self.show_doc = self.set_doc

		global vimView
		self.value = vimView.serverName

	def get_set_string(self):
		global vimView
		vimView.setCommand(serverName=self.value)
		return self.get_show_string(self.value)

	def get_show_string(self, svalue):
		return 'Vim server name: "' + svalue + '"'


### Parameter: vim binary name ###
class ParamBinaryName(gdb.Parameter):
	"""This is part of the VimView plugin."""
	def __init__(self, cmd):
		super(ParamBinaryName, self).__init__(cmd, gdb.COMMAND_SUPPORT, gdb.PARAM_STRING)
		self.set_doc = 'VimView: vim executable name.'
		self.show_doc = self.set_doc

		global vimView
		self.value = vimView.binaryName

	def get_set_string(self):
		global vimView
		vimView.setCommand(binaryName=self.value)
		return self.get_show_string(self.value)

	def get_show_string(self, svalue):
		return 'Vim executable name: "' + svalue + '"'


### Parameter: use tabs in vim ###
class ParamUseTabs(gdb.Parameter):
	"""This is part of the VimView plugin."""
	def __init__(self, cmd):
		super(ParamUseTabs, self).__init__(cmd, gdb.COMMAND_SUPPORT, gdb.PARAM_BOOLEAN)
		self.value = False
		self.set_doc = 'VimView: open files in tabs.'
		self.show_doc = self.set_doc

	def get_set_string(self):
		global vimView
		vimView.setCommand(useTabs=self.value)
		return self.get_show_string(self.value)

	def get_show_string(self, svalue):
		return 'Open files in tabs: ' + _gdbBooleanToStr(svalue)


if __name__ == "__main__":
	if 'vimView' not in globals():
		vimView = VimView()

	try:
		serverName = _getVimServerNameVariable()
		vimView.setCommand(serverName=serverName)
		gdb.write('Vim server name: "' + serverName + '"\n')
	except KeyError:
		serverName = None

	CmdView('vim')
	CmdView('v')
	CmdBreak('vbreak')

	VarCursorWord('vw', 'expand("<cword>")')
	VarCursorWord('ve', 'expand("<cWORD>")')
	VarCursorWord('vf', 'expand("%:p")')
	VarCursorWord('vl', 'line(".")')
	VarCursorWord('vfl', 'expand("%:p") . ":" . line(".")')

	ParamVimViewOnStop('vimview-onstop')
	ParamVimViewOnPrompt('vimview-onprompt')
	ParamServerName('vimview-server')
	ParamBinaryName('vimview-command')
	ParamUseTabs('vimview-tabs')

