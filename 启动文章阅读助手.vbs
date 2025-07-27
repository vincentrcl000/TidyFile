' TidyFile 文章阅读助手 - 静默启动脚本
' 创建时间: 2025-01-27
' 更新时间: 2025-01-27 - 添加进程清理和统一启动逻辑

Option Explicit

Dim objShell, objFSO, strPath, strVenvPath
Dim strCommand, strArgs

' 创建对象
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 获取当前脚本所在目录
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' 检查虚拟环境
strVenvPath = strPath & "\.venv\Scripts\python.exe"
If Not objFSO.FileExists(strVenvPath) Then
    ' 创建虚拟环境
    objShell.Run "python -m venv .venv", 0, True
End If



' 启动文章阅读助手服务器
strCommand = strVenvPath
strArgs = strPath & "\start_viewer_server.py"

' 使用隐藏窗口模式启动服务器
objShell.Run """" & strCommand & """ """ & strArgs & """", 0, False

' 清理对象
Set objShell = Nothing
Set objFSO = Nothing 