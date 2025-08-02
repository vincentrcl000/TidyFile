' TidyFile Article Reader Assistant - Enhanced Startup Script
' Created: 2025-01-27
' Updated: 2025-01-27 - Enhanced cross-computer compatibility and error handling

Option Explicit

Dim objShell, objFSO, strPath, strPythonPath
Dim strCommand, strArgs, intResult

' Create objects
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get current script directory
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Check if Python is available
strPythonPath = "python"
intResult = objShell.Run("python --version", 0, True)
If intResult <> 0 Then
    ' Try other possible Python paths
    If objFSO.FileExists("C:\Python39\python.exe") Then
        strPythonPath = "C:\Python39\python.exe"
    ElseIf objFSO.FileExists("C:\Python310\python.exe") Then
        strPythonPath = "C:\Python310\python.exe"
    ElseIf objFSO.FileExists("C:\Python311\python.exe") Then
        strPythonPath = "C:\Python311\python.exe"
    ElseIf objFSO.FileExists("C:\Users\" & objShell.ExpandEnvironmentStrings("%USERNAME%") & "\AppData\Local\Programs\Python\Python39\python.exe") Then
        strPythonPath = "C:\Users\" & objShell.ExpandEnvironmentStrings("%USERNAME%") & "\AppData\Local\Programs\Python\Python39\python.exe"
    ElseIf objFSO.FileExists("C:\Users\" & objShell.ExpandEnvironmentStrings("%USERNAME%") & "\AppData\Local\Programs\Python\Python310\python.exe") Then
        strPythonPath = "C:\Users\" & objShell.ExpandEnvironmentStrings("%USERNAME%") & "\AppData\Local\Programs\Python\Python310\python.exe"
    ElseIf objFSO.FileExists("C:\Users\" & objShell.ExpandEnvironmentStrings("%USERNAME%") & "\AppData\Local\Programs\Python\Python311\python.exe") Then
        strPythonPath = "C:\Users\" & objShell.ExpandEnvironmentStrings("%USERNAME%") & "\AppData\Local\Programs\Python\Python311\python.exe"
    Else
        MsgBox "Error: Cannot find Python environment, please ensure Python 3.9 or higher is installed", vbCritical, "Startup Failed"
        WScript.Quit 1
    End If
End If

' Check if main program file exists
If Not objFSO.FileExists(strPath & "\start_viewer_server.py") Then
    MsgBox "Error: Cannot find main program file start_viewer_server.py" & vbCrLf & "Current directory: " & strPath, vbCritical, "Startup Failed"
    WScript.Quit 1
End If

' Check if HTML file exists
If Not objFSO.FileExists(strPath & "\viewer.html") Then
    MsgBox "Warning: Cannot find viewer.html file, may affect functionality" & vbCrLf & "Please ensure files are complete", vbInformation, "File Missing"
End If

' Check if JSON file exists (optional)
If Not objFSO.FileExists(strPath & "\ai_organize_result.json") Then
    ' Create safe JSON file
    Dim objFile
    Set objFile = objFSO.CreateTextFile(strPath & "\ai_organize_result.json", True)
    objFile.Write "[{""processing_time"": ""initialization"", ""filename"": ""system_init"", ""summary"": ""safe_file_created_at_startup"", ""status"": ""initialized"", ""operation_type"": ""system_init""}]"
    objFile.Close
    Set objFile = Nothing
End If

' Check if port 80 is occupied
intResult = objShell.Run("netstat -an | findstr :80", 0, True)
If intResult = 0 Then
    ' Port 80 is occupied, try other ports
    MsgBox "Info: Port 80 is occupied, will try other ports", vbInformation, "Port Occupied"
End If

' Start Article Reader Assistant server directly
strCommand = strPythonPath
strArgs = strPath & "\start_viewer_server.py"

' Start server with hidden window
intResult = objShell.Run("""" & strCommand & """ """ & strArgs & """", 0, False)

' Wait for server to start
WScript.Sleep 1000

' Note: Browser will be opened automatically by the server
' No need to open browser here to avoid duplicate windows

' Clean up objects
Set objShell = Nothing
Set objFSO = Nothing 