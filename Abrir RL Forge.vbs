Set WShell = CreateObject("WScript.Shell")
WShell.CurrentDirectory = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\")) & "electron"
WShell.Run "cmd /c npx electron .", 0, False
Set WShell = Nothing
