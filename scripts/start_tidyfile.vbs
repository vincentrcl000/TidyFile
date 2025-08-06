' TidyFile Quick Startup Script
' Created: 2025-08-05

Option Explicit

Dim objShell, objFSO, strPath, strPythonPath
Dim strCommand, strArgs

' Create objects
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get current directory
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Use system Python directly
strPythonPath = "python"

' Check if main program exists
If Not objFSO.FileExists(strPath & "\main.py") Then
    MsgBox "Error: Main program file main.py not found.", vbCritical, "Startup Failed"
    WScript.Quit 1
End If

' Start main program directly
strCommand = strPythonPath
strArgs = strPath & "\main.py"

' Launch with hidden window
objShell.Run """" & strCommand & """ """ & strArgs & """", 0, False

' Clean up
Set objShell = Nothing
Set objFSO = Nothing 