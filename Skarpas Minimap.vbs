Dim fso, scriptDir, pyExe, mainPy, shell
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

pyExe  = scriptDir & "\.venv\Scripts\pythonw.exe"
mainPy = scriptDir & "\main.py"

Set shell = CreateObject("WScript.Shell")
shell.Run """" & pyExe & """ """ & mainPy & """", 0, False
