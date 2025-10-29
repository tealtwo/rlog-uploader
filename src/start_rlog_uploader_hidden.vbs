Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this VBS file is located
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strBatchFile = strScriptDir & "\start_rlog_uploader.bat"

' Run the batch file hidden (0 = hidden window)
objShell.Run Chr(34) & strBatchFile & Chr(34), 0, False

Set objShell = Nothing
Set objFSO = Nothing
