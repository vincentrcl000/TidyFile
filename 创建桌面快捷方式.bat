@echo off
chcp 65001 >nul
echo 正在创建桌面快捷方式...
echo.

:: 获取当前目录
set "CURRENT_DIR=%~dp0"

:: 获取桌面路径
for /f "tokens=3*" %%i in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v Desktop 2^>nul') do set "DESKTOP=%%j"

:: 创建快捷方式的VBS脚本
echo Set WshShell = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
echo Set Shortcut = WshShell.CreateShortcut("%DESKTOP%\智能文件整理器.lnk") >> "%TEMP%\CreateShortcut.vbs"
echo Shortcut.TargetPath = "%CURRENT_DIR%启动文件整理器.bat" >> "%TEMP%\CreateShortcut.vbs"
echo Shortcut.WorkingDirectory = "%CURRENT_DIR%" >> "%TEMP%\CreateShortcut.vbs"
echo Shortcut.Description = "智能文件整理器 - AI驱动的文件自动分类工具" >> "%TEMP%\CreateShortcut.vbs"
echo Shortcut.Save >> "%TEMP%\CreateShortcut.vbs"

:: 执行VBS脚本
cscript "%TEMP%\CreateShortcut.vbs" >nul

:: 清理临时文件
del "%TEMP%\CreateShortcut.vbs"

echo ✅ 桌面快捷方式创建成功！
echo 📍 快捷方式名称：智能文件整理器
echo 🖱️  双击桌面图标即可启动程序
echo.
pause