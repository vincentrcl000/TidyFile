@echo off
chcp 65001 >nul
echo AI文件整理结果查看器 - HTTPS版本
echo ================================================
echo.
echo 正在启动HTTPS服务器...
echo.
python start_viewer_server_https.py
pause 