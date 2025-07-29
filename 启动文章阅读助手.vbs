' TidyFile 文章阅读助手 - 静默启动脚本
' 创建时间: 2025-01-27
' 更新时间: 2025-01-27 - 修复跨电脑兼容性问题

Option Explicit

Dim objShell, objFSO, strPath, strPythonPath
Dim strCommand, strArgs

' 创建对象
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 获取当前脚本所在目录
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' 使用系统Python直接启动，提高兼容性
strPythonPath = "python"

' 检查主程序文件是否存在
If Not objFSO.FileExists(strPath & "\start_viewer_server.py") Then
    MsgBox "Error: Cannot find main program file start_viewer_server.py", vbCritical, "Startup Failed"
    WScript.Quit 1
End If

' 检查HTML文件是否存在
If Not objFSO.FileExists(strPath & "\viewer.html") Then
    MsgBox "Warning: Cannot find viewer.html file, may affect functionality", vbInformation, "File Missing"
End If

' 启动文章阅读助手服务器
strCommand = strPythonPath
strArgs = strPath & "\start_viewer_server.py"

' 使用隐藏窗口模式启动服务器
objShell.Run """" & strCommand & """ """ & strArgs & """", 0, False

' 清理对象
Set objShell = Nothing
Set objFSO = Nothing 