' TidyFile Quick Startup Script
' Created: 2025-07-27

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
If Not objFSO.FileExists(strPath & "\gui_app_tabbed.py") Then
    MsgBox "Error: Main program file gui_app_tabbed.py not found.", vbCritical, "Startup Failed"
    WScript.Quit 1
End If

' Start main program directly
strCommand = strPythonPath
strArgs = strPath & "\gui_app_tabbed.py"

' Launch with hidden window
objShell.Run """" & strCommand & """ """ & strArgs & """", 0, False

' Clean up
Set objShell = Nothing
Set objFSO = Nothing 