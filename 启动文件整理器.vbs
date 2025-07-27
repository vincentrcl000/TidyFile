' TidyFile 智能文件整理器 - 无窗口启动脚本
' 创建时间: 2025-01-27

Option Explicit

Dim objShell, objFSO, strPath, strPythonPath, strVenvPath
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

' 检查依赖包
strCommand = strVenvPath & " -c ""import PIL, ttkbootstrap, PyPDF2, docx, cv2, numpy, requests, openai, bs4"""
objShell.Run strCommand, 0, True

' 如果依赖检查失败，安装依赖
If objShell.Run(strCommand, 0, True) <> 0 Then
    strCommand = strVenvPath & " -m pip install Pillow ttkbootstrap PyPDF2 python-docx opencv-python numpy requests openai beautifulsoup4 html2text fake-useragent markdown send2trash chardet pyyaml coloredlogs pywin32 pypandoc"
    objShell.Run strCommand, 0, True
End If

' 启动主程序
strCommand = strVenvPath
strArgs = strPath & "\gui_app_tabbed.py"

' 使用隐藏窗口模式启动
objShell.Run """" & strCommand & """ """ & strArgs & """", 0, False

' 清理对象
Set objShell = Nothing
Set objFSO = Nothing 