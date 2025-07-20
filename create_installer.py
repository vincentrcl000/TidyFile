#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文件整理器 - Windows 安装包制作脚本

此脚本用于创建 Windows 安装程序，包括：
1. 使用 PyInstaller 打包可执行文件
2. 使用 NSIS 创建安装程序
3. 自动创建桌面快捷方式
4. 添加开始菜单项
5. 支持卸载功能
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import tempfile


class WindowsInstaller:
    """Windows 安装包制作器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.app_name = "智能文件整理器"
        self.app_version = "1.0.0"
        self.app_publisher = "Smart File Organizer"
        self.main_exe = "gui_app_tabbed.py"
        self.exe_name = "智能文件整理器.exe"
        
        # 构建目录
        self.build_dir = self.project_root / "build_installer"
        self.dist_dir = self.build_dir / "dist"
        self.installer_dir = self.build_dir / "installer"
        
        # 确保目录存在
        self.build_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
        self.installer_dir.mkdir(exist_ok=True)
        
    def check_nsis(self) -> bool:
        """检查 NSIS 是否已安装"""
        try:
            result = subprocess.run(["makensis", "/VERSION"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[成功] 检测到 NSIS: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass
            
        print("[错误] 未检测到 NSIS")
        print("请从以下地址下载并安装 NSIS:")
        print("https://nsis.sourceforge.io/Download")
        print("安装后请确保 makensis.exe 在系统 PATH 中")
        return False
        
    def check_pyinstaller(self) -> bool:
        """检查 PyInstaller 是否已安装"""
        try:
            result = subprocess.run(["pyinstaller", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[成功] 检测到 PyInstaller: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass
            
        print("[错误] 未检测到 PyInstaller")
        print("正在安装 PyInstaller...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                         check=True)
            print("[成功] PyInstaller 安装完成")
            return True
        except subprocess.CalledProcessError:
            print("[错误] PyInstaller 安装失败")
            return False
            
    def create_pyinstaller_spec(self) -> Path:
        """创建 PyInstaller 规格文件"""
        spec_content = f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{self.main_exe}'],
    pathex=['{self.project_root}'],
    binaries=[],
    datas=[
        ('static', 'static'),
        ('templates', 'templates'),
        ('*.py', '.'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'ttkbootstrap',
        'requests',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'threading',
        'queue',
        'json',
        'os',
        'shutil',
        'pathlib',
        'datetime',
        'subprocess',
        'webbrowser',
        'http.server',
        'socketserver',
        'urllib.parse',
        'time',
        'logging',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self.exe_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
        
        spec_file = self.build_dir / f"{self.app_name}.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
            
        print(f"[成功] PyInstaller 规格文件已创建: {spec_file}")
        return spec_file
        
    def build_executable(self, spec_file: Path) -> bool:
        """使用 PyInstaller 构建可执行文件"""
        print("\n开始构建可执行文件...")
        
        try:
            cmd = [
                "pyinstaller",
                "--clean",
                "--noconfirm",
                "--distpath", str(self.dist_dir),
                "--workpath", str(self.build_dir / "work"),
                str(spec_file)
            ]
            
            print(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=self.project_root, 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                exe_path = self.dist_dir / self.exe_name
                if exe_path.exists():
                    print(f"[成功] 可执行文件已创建: {exe_path}")
                    return True
                else:
                    print("[错误] 可执行文件未找到")
                    return False
            else:
                print(f"[错误] PyInstaller 构建失败:")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"[错误] 构建过程中发生异常: {e}")
            return False
            
    def create_nsis_script(self) -> Path:
        """创建 NSIS 安装脚本"""
        nsis_script = f'''
; 智能文件整理器安装脚本
; 使用 NSIS 3.0+ 编译

!define APP_NAME "{self.app_name}"
!define APP_VERSION "{self.app_version}"
!define APP_PUBLISHER "{self.app_publisher}"
!define APP_EXE "{self.exe_name}"
!define APP_UNINSTALLER "Uninstall.exe"

; 安装程序属性
Name "${{APP_NAME}}"
OutFile "{self.installer_dir / f'{self.app_name}_v{self.app_version}_Setup.exe'}"
InstallDir "$PROGRAMFILES64\\${{APP_NAME}}"
InstallDirRegKey HKLM "Software\\${{APP_NAME}}" "InstallDir"
RequestExecutionLevel admin

; 现代界面
!include "MUI2.nsh"

; 界面设置
!define MUI_ABORTWARNING
!define MUI_ICON "${{NSISDIR}}\\Contrib\\Graphics\\Icons\\modern-install.ico"
!define MUI_UNICON "${{NSISDIR}}\\Contrib\\Graphics\\Icons\\modern-uninstall.ico"

; 安装页面
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${{NSISDIR}}\\Docs\\Modern UI\\License.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\\${{APP_EXE}}"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\\使用说明.md"
!insertmacro MUI_PAGE_FINISH

; 卸载页面
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; 语言
!insertmacro MUI_LANGUAGE "SimpChinese"

; 版本信息
VIProductVersion "{self.app_version}.0"
VIAddVersionKey /LANG=${{LANG_SIMPCHINESE}} "ProductName" "${{APP_NAME}}"
VIAddVersionKey /LANG=${{LANG_SIMPCHINESE}} "CompanyName" "${{APP_PUBLISHER}}"
VIAddVersionKey /LANG=${{LANG_SIMPCHINESE}} "FileVersion" "${{APP_VERSION}}"
VIAddVersionKey /LANG=${{LANG_SIMPCHINESE}} "ProductVersion" "${{APP_VERSION}}"
VIAddVersionKey /LANG=${{LANG_SIMPCHINESE}} "FileDescription" "智能文件整理器安装程序"
VIAddVersionKey /LANG=${{LANG_SIMPCHINESE}} "LegalCopyright" "© 2024 ${{APP_PUBLISHER}}"

; 安装部分
Section "主程序" SecMain
    SectionIn RO
    
    ; 设置输出路径
    SetOutPath "$INSTDIR"
    
    ; 复制文件
    File "{self.dist_dir / self.exe_name}"
    File /r "{self.dist_dir}\\*"
    
    ; 创建使用说明
    FileOpen $0 "$INSTDIR\\使用说明.md" w
    FileWrite $0 "# ${{APP_NAME}} v${{APP_VERSION}}$\r$\n$\r$\n"
    FileWrite $0 "## 使用方法$\r$\n$\r$\n"
    FileWrite $0 "1. 确保已安装 Ollama 服务$\r$\n"
    FileWrite $0 "2. 下载 AI 模型: ollama pull gemma2:2b$\r$\n"
    FileWrite $0 "3. 双击桌面图标启动程序$\r$\n$\r$\n"
    FileWrite $0 "## 系统要求$\r$\n$\r$\n"
    FileWrite $0 "- Windows 10/11 (64位)$\r$\n"
    FileWrite $0 "- 至少 8GB 内存$\r$\n"
    FileWrite $0 "- 已安装 Ollama 服务$\r$\n$\r$\n"
    FileWrite $0 "安装时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}$\r$\n"
    FileClose $0
    
    ; 写入注册表
    WriteRegStr HKLM "Software\\${{APP_NAME}}" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\\${{APP_NAME}}" "Version" "${{APP_VERSION}}"
    
    ; 写入卸载信息
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "DisplayName" "${{APP_NAME}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "UninstallString" "$INSTDIR\\${{APP_UNINSTALLER}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "DisplayIcon" "$INSTDIR\\${{APP_EXE}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "Publisher" "${{APP_PUBLISHER}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "DisplayVersion" "${{APP_VERSION}}"
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "NoModify" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}" "NoRepair" 1
    
    ; 创建卸载程序
    WriteUninstaller "$INSTDIR\\${{APP_UNINSTALLER}}"
    
SectionEnd

; 快捷方式部分
Section "桌面快捷方式" SecDesktop
    CreateShortcut "$DESKTOP\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_EXE}}" "" "$INSTDIR\\${{APP_EXE}}" 0
SectionEnd

Section "开始菜单" SecStartMenu
    CreateDirectory "$SMPROGRAMS\\${{APP_NAME}}"
    CreateShortcut "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk" "$INSTDIR\\${{APP_EXE}}" "" "$INSTDIR\\${{APP_EXE}}" 0
    CreateShortcut "$SMPROGRAMS\\${{APP_NAME}}\\使用说明.lnk" "$INSTDIR\\使用说明.md"
    CreateShortcut "$SMPROGRAMS\\${{APP_NAME}}\\卸载.lnk" "$INSTDIR\\${{APP_UNINSTALLER}}"
SectionEnd

; 组件描述
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${{SecMain}} "安装 ${{APP_NAME}} 主程序文件"
    !insertmacro MUI_DESCRIPTION_TEXT ${{SecDesktop}} "在桌面创建快捷方式"
    !insertmacro MUI_DESCRIPTION_TEXT ${{SecStartMenu}} "在开始菜单创建程序组"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; 卸载部分
Section "Uninstall"
    ; 删除文件
    Delete "$INSTDIR\\${{APP_EXE}}"
    Delete "$INSTDIR\\${{APP_UNINSTALLER}}"
    Delete "$INSTDIR\\使用说明.md"
    RMDir /r "$INSTDIR"
    
    ; 删除快捷方式
    Delete "$DESKTOP\\${{APP_NAME}}.lnk"
    Delete "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk"
    Delete "$SMPROGRAMS\\${{APP_NAME}}\\使用说明.lnk"
    Delete "$SMPROGRAMS\\${{APP_NAME}}\\卸载.lnk"
    RMDir "$SMPROGRAMS\\${{APP_NAME}}"
    
    ; 删除注册表项
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APP_NAME}}"
    DeleteRegKey HKLM "Software\\${{APP_NAME}}"
    
SectionEnd
'''
        
        nsis_file = self.installer_dir / f"{self.app_name}.nsi"
        with open(nsis_file, 'w', encoding='utf-8') as f:
            f.write(nsis_script)
            
        print(f"[成功] NSIS 脚本已创建: {nsis_file}")
        return nsis_file
        
    def build_installer(self, nsis_file: Path) -> bool:
        """使用 NSIS 构建安装程序"""
        print("\n开始构建安装程序...")
        
        try:
            cmd = ["makensis", str(nsis_file)]
            print(f"执行命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                installer_path = self.installer_dir / f"{self.app_name}_v{self.app_version}_Setup.exe"
                if installer_path.exists():
                    print(f"[成功] 安装程序已创建: {installer_path}")
                    return True
                else:
                    print("[错误] 安装程序文件未找到")
                    return False
            else:
                print(f"[错误] NSIS 构建失败:")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"[错误] 构建安装程序时发生异常: {e}")
            return False
            
    def create_batch_installer(self) -> Path:
        """创建简化的批处理安装脚本（备用方案）"""
        batch_content = f'''@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo {self.app_name} 安装程序
echo ================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [错误] 需要管理员权限运行此安装程序
    echo 请右键点击此文件，选择"以管理员身份运行"
    pause
    exit /b 1
)

:: 设置安装目录
set "INSTALL_DIR=%ProgramFiles%\\{self.app_name}"
echo 安装目录: !INSTALL_DIR!
echo.

:: 创建安装目录
if not exist "!INSTALL_DIR!" (
    mkdir "!INSTALL_DIR!"
    if !errorlevel! neq 0 (
        echo [错误] 无法创建安装目录
        pause
        exit /b 1
    )
)

:: 复制文件
echo 正在复制程序文件...
copy "{self.exe_name}" "!INSTALL_DIR!\\" >nul
if !errorlevel! neq 0 (
    echo [错误] 复制主程序失败
    pause
    exit /b 1
)

:: 创建桌面快捷方式
echo 正在创建桌面快捷方式...
set "DESKTOP=%USERPROFILE%\\Desktop"
set "SHORTCUT=!DESKTOP!\\{self.app_name}.lnk"

:: 使用 PowerShell 创建快捷方式
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('!SHORTCUT!'); $Shortcut.TargetPath = '!INSTALL_DIR!\\{self.exe_name}'; $Shortcut.WorkingDirectory = '!INSTALL_DIR!'; $Shortcut.Description = '{self.app_name}'; $Shortcut.Save()"

if !errorlevel! equ 0 (
    echo [成功] 桌面快捷方式已创建
) else (
    echo [警告] 桌面快捷方式创建失败
)

:: 创建开始菜单快捷方式
echo 正在创建开始菜单快捷方式...
set "STARTMENU=%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs"
set "PROGRAM_GROUP=!STARTMENU!\\{self.app_name}"

if not exist "!PROGRAM_GROUP!" (
    mkdir "!PROGRAM_GROUP!"
)

set "START_SHORTCUT=!PROGRAM_GROUP!\\{self.app_name}.lnk"
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('!START_SHORTCUT!'); $Shortcut.TargetPath = '!INSTALL_DIR!\\{self.exe_name}'; $Shortcut.WorkingDirectory = '!INSTALL_DIR!'; $Shortcut.Description = '{self.app_name}'; $Shortcut.Save()"

if !errorlevel! equ 0 (
    echo [成功] 开始菜单快捷方式已创建
) else (
    echo [警告] 开始菜单快捷方式创建失败
)

:: 创建使用说明
echo 正在创建使用说明...
echo # {self.app_name} v{self.app_version} > "!INSTALL_DIR!\\使用说明.txt"
echo. >> "!INSTALL_DIR!\\使用说明.txt"
echo ## 使用方法 >> "!INSTALL_DIR!\\使用说明.txt"
echo. >> "!INSTALL_DIR!\\使用说明.txt"
echo 1. 确保已安装 Ollama 服务 >> "!INSTALL_DIR!\\使用说明.txt"
echo 2. 下载 AI 模型: ollama pull gemma2:2b >> "!INSTALL_DIR!\\使用说明.txt"
echo 3. 双击桌面图标启动程序 >> "!INSTALL_DIR!\\使用说明.txt"
echo. >> "!INSTALL_DIR!\\使用说明.txt"
echo 安装时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} >> "!INSTALL_DIR!\\使用说明.txt"

echo.
echo ================================
echo 安装完成！
echo.
echo 程序已安装到: !INSTALL_DIR!
echo 桌面快捷方式: !DESKTOP!\\{self.app_name}.lnk
echo 开始菜单: !PROGRAM_GROUP!
echo.
echo 使用前请确保：
echo 1. 已安装 Ollama 服务
echo 2. 已下载 AI 模型 (ollama pull gemma2:2b)
echo.
echo 按任意键启动程序...
pause >nul

start "" "!INSTALL_DIR!\\{self.exe_name}"
'''
        
        batch_file = self.installer_dir / f"{self.app_name}_安装程序.bat"
        with open(batch_file, 'w', encoding='gbk') as f:
            f.write(batch_content)
            
        print(f"[成功] 批处理安装程序已创建: {batch_file}")
        return batch_file
        
    def build_all(self) -> bool:
        """执行完整的构建流程"""
        print(f"{self.app_name} - Windows 安装包制作器")
        print("=" * 50)
        
        try:
            # 检查 PyInstaller
            if not self.check_pyinstaller():
                return False
                
            # 创建 PyInstaller 规格文件
            spec_file = self.create_pyinstaller_spec()
            
            # 构建可执行文件
            if not self.build_executable(spec_file):
                return False
                
            # 检查 NSIS
            if self.check_nsis():
                # 创建 NSIS 脚本
                nsis_file = self.create_nsis_script()
                
                # 构建安装程序
                if self.build_installer(nsis_file):
                    print("\n[成功] NSIS 安装程序构建完成")
                else:
                    print("\n[警告] NSIS 安装程序构建失败，将创建批处理安装程序")
                    self.create_batch_installer()
            else:
                print("\n[信息] 未安装 NSIS，创建批处理安装程序")
                self.create_batch_installer()
                
            print("\n" + "=" * 50)
            print("构建完成！")
            print(f"输出目录: {self.installer_dir.absolute()}")
            print("\n文件说明：")
            print(f"- {self.exe_name}: 可执行文件")
            if (self.installer_dir / f"{self.app_name}_v{self.app_version}_Setup.exe").exists():
                print(f"- {self.app_name}_v{self.app_version}_Setup.exe: NSIS 安装程序")
            if (self.installer_dir / f"{self.app_name}_安装程序.bat").exists():
                print(f"- {self.app_name}_安装程序.bat: 批处理安装程序")
            
            print("\n使用方法：")
            print("1. 运行安装程序")
            print("2. 按提示完成安装")
            print("3. 桌面和开始菜单将自动创建快捷方式")
            
            return True
            
        except Exception as e:
            print(f"[错误] 构建过程中发生错误: {e}")
            return False


def main():
    """主函数"""
    installer = WindowsInstaller()
    
    if installer.build_all():
        print("\n构建成功完成！")
        sys.exit(0)
    else:
        print("\n构建失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()