#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地HTTP服务器启动脚本
用于解决浏览器CORS策略限制，使ai_result_viewer.html能够正常加载JSON文件
支持局域网访问

作者: AI助手
创建时间: 2025-01-20
更新时间: 2025-01-27 - 重构为统一的服务管理逻辑
"""

import http.server
import socketserver
import webbrowser
import os
import sys
import json
import urllib.parse
import subprocess
import threading
import time
import socket
from pathlib import Path
from datetime import datetime

def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        # 创建一个UDP套接字连接到外部地址
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        # 如果获取失败，返回默认地址
        return "0.0.0.0"

def check_server_running(port=80):
    """检查服务器是否已经在运行"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except:
        return False



def open_browser_with_urls(local_ip, port=80):
    """打开浏览器并显示访问地址"""
    try:
        # 根据端口构建正确的URL
        if port == 80:
            url = "http://localhost/viewer.html"
        else:
            url = f"http://localhost:{port}/viewer.html"
        
        # 打开浏览器
        webbrowser.open(url)
        
    except Exception as e:
        print(f"无法自动打开浏览器: {e}")
        if port == 80:
            print(f"请手动访问: http://localhost/viewer.html")
        else:
            print(f"请手动访问: http://localhost:{port}/viewer.html")

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    自定义HTTP请求处理器，支持清理重复文件的API
    """
    
    def end_headers(self):
        """重写end_headers方法，添加缓存控制头"""
        # 为HTML文件添加缓存控制头，强制浏览器重新加载
        if self.path.endswith('.html'):
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == '/api/clean-duplicates':
            self.handle_clean_duplicates()
        elif self.path == '/api/check-paths':
            self.handle_check_paths()
        elif self.path == '/api/search-and-update-paths':
            self.handle_search_and_update_paths()
        elif self.path == '/api/check-and-fix-paths':
            self.handle_check_and_fix_paths()
        elif self.path == '/api/shutdown':
            self.handle_shutdown()
        elif self.path == '/api/heartbeat':
            self.handle_heartbeat()
        elif self.path == '/api/open-file':
            self.handle_open_file()
        else:
            self.send_error(404, "API endpoint not found")
    
    def do_GET(self):
        """处理GET请求"""
        if self.path.startswith('/api/download-file'):
            self.handle_download_file()
        elif self.path == '/api/heartbeat':
            self.handle_heartbeat()
        else:
            super().do_GET()
    
    def handle_clean_duplicates(self):
        """处理清理重复文件的请求
        只按文件名判断重复，保留每个文件的最新记录
        """
        try:
            json_file = Path('ai_organize_result.json')
            
            if not json_file.exists():
                self.send_json_response({'success': False, 'message': 'JSON文件不存在'})
                return
            
            # 读取现有数据
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.send_json_response({'success': False, 'message': f'JSON文件格式错误: {str(e)}'})
                return
            except Exception as e:
                self.send_json_response({'success': False, 'message': f'读取JSON文件失败: {str(e)}'})
                return
            
            # 清理重复文件
            cleaned_data = self.remove_duplicate_files(data)
            
            # 保存清理后的数据
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
            
            removed_count = len(data) - len(cleaned_data)
            
            self.send_json_response({
                'success': True, 
                'message': f'成功清理 {removed_count} 条重复记录',
                'original_count': len(data),
                'cleaned_count': len(cleaned_data),
                'removed_count': removed_count
            })
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'清理失败: {str(e)}'})
    
    def handle_check_and_fix_paths(self):
        """处理检查和修复文件路径的请求"""
        try:
            json_file = Path('ai_organize_result.json')
            
            if not json_file.exists():
                self.send_json_response({'success': False, 'message': 'JSON文件不存在'})
                return
            
            # 读取现有数据
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.send_json_response({'success': False, 'message': f'JSON文件格式错误: {str(e)}'})
                return
            except Exception as e:
                self.send_json_response({'success': False, 'message': f'读取JSON文件失败: {str(e)}'})
                return
            
            # 检查并修复文件路径
            fixed_data = self.check_and_fix_file_paths(data)
            
            # 保存修复后的数据
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(fixed_data, f, ensure_ascii=False, indent=2)
            
            # 统计修复结果
            total_files = len(fixed_data)
            valid_paths = sum(1 for item in fixed_data if os.path.exists(item.get('最终目标路径', '')))
            fixed_paths = sum(1 for item in fixed_data if item.get('路径已修复', False))
            not_found = total_files - valid_paths - fixed_paths
            
            self.send_json_response({
                'success': True,
                'message': f'路径检查完成',
                'total_files': total_files,
                'valid_paths': valid_paths,
                'fixed_paths': fixed_paths,
                'not_found': not_found
            })
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'路径检查失败: {str(e)}'})
    
    def handle_check_paths(self):
        """处理路径检查请求 - 只检查不修复"""
        try:
            json_file = Path('ai_organize_result.json')
            
            if not json_file.exists():
                self.send_json_response({'success': False, 'message': 'JSON文件不存在'})
                return
            
            # 读取现有数据
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.send_json_response({'success': False, 'message': f'JSON文件格式错误: {str(e)}'})
                return
            except Exception as e:
                self.send_json_response({'success': False, 'message': f'读取JSON文件失败: {str(e)}'})
                return
            
            # 只进行路径检查
            check_result = self.check_file_paths_only(data)
            
            self.send_json_response({
                'success': True,
                'message': f'路径检查完成',
                'total_files': check_result['total'],
                'valid_paths': check_result['valid'],
                'missing_paths': check_result['missing'],
                'checked': check_result['total']
            })
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'路径检查失败: {str(e)}'})
    
    def handle_search_and_update_paths(self):
        """处理搜索和更新文件路径的请求"""
        try:
            json_file = Path('ai_organize_result.json')
            
            if not json_file.exists():
                self.send_json_response({'success': False, 'message': 'JSON文件不存在'})
                return
            
            # 读取现有数据
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.send_json_response({'success': False, 'message': f'JSON文件格式错误: {str(e)}'})
                return
            except Exception as e:
                self.send_json_response({'success': False, 'message': f'读取JSON文件失败: {str(e)}'})
                return
            
            # 搜索并更新文件路径
            updated_data = self.search_and_update_file_paths(data)
            
            # 保存更新后的数据
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)
            
            # 统计更新结果
            total_files = len(updated_data)
            valid_paths = sum(1 for item in updated_data if os.path.exists(item.get('最终目标路径', '')))
            fixed_paths = sum(1 for item in updated_data if item.get('路径已修复', False))
            not_found = total_files - valid_paths
            
            self.send_json_response({
                'success': True,
                'message': f'搜索和更新完成',
                'total_files': total_files,
                'valid_paths': valid_paths,
                'fixed_paths': fixed_paths,
                'not_found': not_found,
                'checked': total_files,
                'current_file': '更新完成',
                'last_fixed': None
            })
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'搜索和更新失败: {str(e)}'})
    
    def handle_shutdown(self):
        """处理关闭服务器的请求"""
        try:
            # 先发送响应
            self.send_json_response({'success': True, 'message': '服务器即将关闭'})
            
            # 强制退出整个Python进程
            import os
            import sys
            import signal
            
            # 获取当前进程ID
            pid = os.getpid()
            
            # 在Windows上使用taskkill强制终止进程
            if os.name == 'nt':
                import subprocess
                # 立即执行taskkill，不等待
                subprocess.Popen(['taskkill', '/F', '/PID', str(pid)], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                # 在Unix系统上发送SIGKILL信号
                os.kill(pid, signal.SIGKILL)
            
            # 如果上述方法都失败，使用os._exit
            os._exit(0)
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'关闭失败: {str(e)}'})
    
    def handle_heartbeat(self):
        """处理心跳检测请求"""
        import time
        self.send_json_response({
            'success': True, 
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': '服务器运行正常'
        })
    
    def check_and_fix_file_paths(self, data):
        """检查并修复文件路径"""
        fixed_data = []
        
        for item in data:
            target_path = item.get('最终目标路径', '')
            if target_path and os.path.exists(target_path):
                # 路径存在，无需修复
                item['路径已修复'] = False
                fixed_data.append(item)
                continue
            
            # 路径不存在，尝试修复
            file_name = item.get('文件名', '')
            if not file_name:
                item['路径已修复'] = False
                fixed_data.append(item)
                continue
            
            # 搜索文件
            found_path = self.search_file_in_system(file_name)
            if found_path:
                item['最终目标路径'] = found_path
                item['路径已修复'] = True
                print(f"修复路径: {file_name} -> {found_path}")
            else:
                item['路径已修复'] = False
            
            fixed_data.append(item)
        
        return fixed_data
    
    def check_file_paths_only(self, data):
        """只检查文件路径是否存在，不进行搜索"""
        # 过滤掉迁移失败的文件
        valid_data = [item for item in data if '失败' not in (item.get('处理状态', ''))]
        total_files = len(valid_data)
        valid_count = 0
        missing_count = 0
        
        print(f"开始检查：验证 {total_files} 个文件的路径...")
        
        for i, item in enumerate(valid_data):
            target_path = item.get('最终目标路径', '')
            file_name = item.get('文件名', '')
            
            if not file_name:
                missing_count += 1
                continue
            
            # 检查路径是否存在
            if target_path and os.path.exists(target_path):
                valid_count += 1
            else:
                missing_count += 1
            
            # 每100个文件打印一次进度
            if (i + 1) % 100 == 0:
                print(f"进度: {i + 1}/{total_files} - 路径正常: {valid_count}个, 文件已不在原位置: {missing_count}个")
        
        print(f"检查完成 - 正常: {valid_count}, 文件已不在原位置: {missing_count}")
        return {'total': total_files, 'valid': valid_count, 'missing': missing_count}
    
    def search_and_update_file_paths(self, data):
        """搜索并更新文件路径"""
        # 过滤掉迁移失败的文件
        valid_data = [item for item in data if '失败' not in (item.get('处理状态', ''))]
        total_files = len(valid_data)
        fixed_count = 0
        not_found_count = 0
        need_search_files = []
        
        print(f"开始搜索：为 {total_files} 个文件搜索当前位置...")
        
        # 第一轮：找出需要搜索的文件
        for i, item in enumerate(valid_data):
            target_path = item.get('最终目标路径', '')
            file_name = item.get('文件名', '')
            
            if not file_name:
                continue
            
            # 如果路径不存在，需要搜索
            if not (target_path and os.path.exists(target_path)):
                need_search_files.append((i, item))
        
        print(f"需要搜索的文件数: {len(need_search_files)}")
        
        # 第二轮：搜索文件
        for search_index, (original_index, item) in enumerate(need_search_files):
            file_name = item.get('文件名', '')
            print(f"搜索进度: {search_index + 1}/{len(need_search_files)} - 搜索文件: {file_name}")
            
            # 搜索文件
            found_path = self.search_file_in_system(file_name)
            
            if found_path:
                item['最终目标路径'] = found_path
                item['路径已修复'] = True
                fixed_count += 1
                print(f"搜索成功: {file_name} -> {found_path}")
            else:
                item['路径已修复'] = False
                not_found_count += 1
                print(f"搜索失败: {file_name}")
            
            # 更新原始数据
            data[original_index] = item
        
        print(f"搜索完成 - 修复: {fixed_count}, 未找到: {not_found_count}")
        return data
    
    def search_file_in_system(self, file_name):
        """在系统中搜索文件"""
        # 首先尝试使用Windows API搜索
        found_path = self.search_with_windows_api(file_name)
        if found_path:
            return found_path
        
        # 如果Windows API搜索失败，尝试在C盘用户目录搜索
        found_path = self.search_c_drive_user_dirs(file_name)
        if found_path:
            return found_path
        
        # 最后尝试备用搜索方法
        return self.fallback_search(file_name)
    
    def search_with_windows_api(self, file_name):
        """使用Windows API搜索文件"""
        try:
            import subprocess
            # 使用where命令搜索文件
            result = subprocess.run(['where', file_name], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines and lines[0]:
                    return lines[0]
        except Exception:
            pass
        return None
    
    def search_c_drive_user_dirs(self, file_name):
        """在C盘用户目录搜索文件"""
        try:
            # 搜索常见的用户目录
            search_dirs = [
                os.path.expanduser("~"),  # 当前用户目录
                os.path.expanduser("~/Desktop"),  # 桌面
                os.path.expanduser("~/Documents"),  # 文档
                os.path.expanduser("~/Downloads"),  # 下载
                "C:/Users",  # 所有用户目录
            ]
            
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    found_path = self.search_file_recursive(search_dir, file_name, max_depth=3)
                    if found_path:
                        return found_path
            
            # 如果上述目录没找到，尝试更广泛的搜索
            return self.search_c_drive_user_dirs_fallback(file_name)
            
        except Exception:
            return None
    
    def fallback_search(self, file_name):
        """备用搜索方法"""
        try:
            # 在常见目录中搜索
            common_dirs = [
                "C:/",
                "D:/",
                "E:/",
                os.path.expanduser("~"),
            ]
            
            for base_dir in common_dirs:
                if os.path.exists(base_dir):
                    found_path = self.search_file_recursive(base_dir, file_name, max_depth=2)
                    if found_path:
                        return found_path
        except Exception:
            pass
        return None
    
    def search_c_drive_user_dirs_fallback(self, file_name):
        """在C盘用户目录的备用搜索方法"""
        try:
            users_dir = "C:/Users"
            if not os.path.exists(users_dir):
                return None
            
            # 遍历用户目录
            for user_dir in os.listdir(users_dir):
                user_path = os.path.join(users_dir, user_dir)
                if os.path.isdir(user_path):
                    # 在用户目录的常见子目录中搜索
                    sub_dirs = ["Desktop", "Documents", "Downloads", "Pictures", "Videos"]
                    for sub_dir in sub_dirs:
                        sub_path = os.path.join(user_path, sub_dir)
                        if os.path.exists(sub_path):
                            found_path = self.search_file_recursive(sub_path, file_name, max_depth=2)
                            if found_path:
                                return found_path
        except Exception:
            pass
        return None
    
    def search_file_recursive(self, directory, file_name, max_depth=3):
        """递归搜索文件"""
        try:
            for root, dirs, files in os.walk(directory):
                # 检查深度
                depth = root[len(directory):].count(os.sep)
                if depth > max_depth:
                    continue
                
                # 在当前目录中搜索文件
                if file_name in files:
                    return os.path.join(root, file_name)
                
                # 模糊匹配（忽略大小写）
                for file in files:
                    if file.lower() == file_name.lower():
                        return os.path.join(root, file)
        except Exception:
            pass
        return None
    
    def handle_open_file(self):
        """处理打开文件的请求"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            file_path = data.get('filePath', '')
            print(f"收到打开文件请求: {file_path}")
            
            if not file_path:
                print("文件路径为空")
                self.send_json_response({'success': False, 'error': '文件路径为空'})
                return
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"文件不存在: {file_path}")
                self.send_json_response({'success': False, 'error': '文件不存在'})
                return
            
            # 获取文件信息
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            print(f"文件信息: 名称={file_name}, 扩展名={file_ext}")
            
            # 使用系统默认程序打开文件
            try:
                if os.name == 'nt':  # Windows
                    print("检测到Windows系统")
                    # 对于Office文件，尝试使用特定的程序打开
                    if self.is_office_file(file_ext):
                        print(f"检测到Office文件: {file_ext}")
                        success = self.open_office_file_windows(file_path, file_ext)
                        print(f"Office文件打开结果: {success}")
                    else:
                        print(f"使用系统默认程序打开: {file_path}")
                        # 使用系统默认程序
                        os.startfile(file_path)
                        success = True
                else:  # Linux/Mac
                    print("检测到非Windows系统")
                    subprocess.run(['xdg-open', file_path])
                    success = True
                
                if success:
                    print(f"文件打开成功: {file_name}")
                    self.send_json_response({
                        'success': True, 
                        'message': f'文件 "{file_name}" 正在使用系统默认程序打开'
                    })
                else:
                    print(f"文件打开失败: {file_name}")
                    self.send_json_response({
                        'success': False, 
                        'error': f'无法找到合适的程序打开 {file_name}'
                    })
                    
            except Exception as e:
                print(f"打开文件异常: {e}")
                self.send_json_response({'success': False, 'error': f'打开文件失败: {str(e)}'})
                
        except Exception as e:
            print(f"处理请求异常: {e}")
            self.send_json_response({'success': False, 'error': f'处理请求失败: {str(e)}'})
    
    def is_office_file(self, file_ext):
        """判断是否为Office文件"""
        office_extensions = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}
        return file_ext in office_extensions
    
    def open_office_file_windows(self, file_path, file_ext):
        """在Windows上打开Office文件"""
        print(f"尝试打开Office文件: {file_path}")
        
        # 确保文件路径是绝对路径
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return False
        
        # 首先尝试使用系统默认程序打开（推荐方式）
        try:
            print("尝试使用系统默认程序打开...")
            os.startfile(file_path)
            print("系统默认程序打开成功")
            return True
        except Exception as e:
            print(f"使用系统默认程序打开失败: {e}")
        
        # 如果系统默认程序失败，尝试使用特定的Office程序
        try:
            program_map = {
                '.doc': 'WINWORD.EXE',
                '.docx': 'WINWORD.EXE',
                '.xls': 'EXCEL.EXE',
                '.xlsx': 'EXCEL.EXE',
                '.ppt': 'POWERPNT.EXE',
                '.pptx': 'POWERPNT.EXE'
            }
            
            program_name = program_map.get(file_ext)
            if program_name:
                print(f"尝试使用 {program_name} 打开...")
                # 尝试启动Office程序，使用完整路径
                subprocess.Popen([program_name, file_path], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW)
                print(f"{program_name} 启动成功")
                return True
                
        except Exception as e2:
            print(f"使用Office程序打开失败: {e2}")
            
        # 尝试使用完整路径的Office程序
        try:
            office_paths = {
                '.doc': [
                    # Microsoft Office
                    r'C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE',
                    r'C:\Program Files\Microsoft Office\Office16\WINWORD.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\Office16\WINWORD.EXE',
                    r'C:\Program Files\Microsoft Office\root\Office15\WINWORD.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office15\WINWORD.EXE',
                    # WPS Office
                    r'C:\Program Files (x86)\WPS Office\11.1.0.11609\office6\wps.exe',
                    r'C:\Program Files\WPS Office\11.1.0.11609\office6\wps.exe',
                    r'C:\Program Files (x86)\WPS Office\12.1.0.14509\office6\wps.exe',
                    r'C:\Program Files\WPS Office\12.1.0.14509\office6\wps.exe'
                ],
                '.docx': [
                    # Microsoft Office
                    r'C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE',
                    r'C:\Program Files\Microsoft Office\Office16\WINWORD.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\Office16\WINWORD.EXE',
                    r'C:\Program Files\Microsoft Office\root\Office15\WINWORD.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office15\WINWORD.EXE',
                    # WPS Office
                    r'C:\Program Files (x86)\WPS Office\11.1.0.11609\office6\wps.exe',
                    r'C:\Program Files\WPS Office\11.1.0.11609\office6\wps.exe',
                    r'C:\Program Files (x86)\WPS Office\12.1.0.14509\office6\wps.exe',
                    r'C:\Program Files\WPS Office\12.1.0.14509\office6\wps.exe'
                ],
                '.xls': [
                    # Microsoft Office
                    r'C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE',
                    r'C:\Program Files\Microsoft Office\Office16\EXCEL.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE',
                    r'C:\Program Files\Microsoft Office\root\Office15\EXCEL.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office15\EXCEL.EXE',
                    # WPS Office
                    r'C:\Program Files (x86)\WPS Office\11.1.0.11609\office6\et.exe',
                    r'C:\Program Files\WPS Office\11.1.0.11609\office6\et.exe',
                    r'C:\Program Files (x86)\WPS Office\12.1.0.14509\office6\et.exe',
                    r'C:\Program Files\WPS Office\12.1.0.14509\office6\et.exe'
                ],
                '.xlsx': [
                    # Microsoft Office
                    r'C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE',
                    r'C:\Program Files\Microsoft Office\Office16\EXCEL.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE',
                    r'C:\Program Files\Microsoft Office\root\Office15\EXCEL.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office15\EXCEL.EXE',
                    # WPS Office
                    r'C:\Program Files (x86)\WPS Office\11.1.0.11609\office6\et.exe',
                    r'C:\Program Files\WPS Office\11.1.0.11609\office6\et.exe',
                    r'C:\Program Files (x86)\WPS Office\12.1.0.14509\office6\et.exe',
                    r'C:\Program Files\WPS Office\12.1.0.14509\office6\et.exe'
                ],
                '.ppt': [
                    # Microsoft Office
                    r'C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE',
                    r'C:\Program Files\Microsoft Office\Office16\POWERPNT.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\Office16\POWERPNT.EXE',
                    r'C:\Program Files\Microsoft Office\root\Office15\POWERPNT.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office15\POWERPNT.EXE',
                    # WPS Office
                    r'C:\Program Files (x86)\WPS Office\11.1.0.11609\office6\wpp.exe',
                    r'C:\Program Files\WPS Office\11.1.0.11609\office6\wpp.exe',
                    r'C:\Program Files (x86)\WPS Office\12.1.0.14509\office6\wpp.exe',
                    r'C:\Program Files\WPS Office\12.1.0.14509\office6\wpp.exe'
                ],
                '.pptx': [
                    # Microsoft Office
                    r'C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE',
                    r'C:\Program Files\Microsoft Office\Office16\POWERPNT.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\Office16\POWERPNT.EXE',
                    r'C:\Program Files\Microsoft Office\root\Office15\POWERPNT.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office15\POWERPNT.EXE',
                    # WPS Office
                    r'C:\Program Files (x86)\WPS Office\11.1.0.11609\office6\wpp.exe',
                    r'C:\Program Files\WPS Office\11.1.0.11609\office6\wpp.exe',
                    r'C:\Program Files (x86)\WPS Office\12.1.0.14509\office6\wpp.exe',
                    r'C:\Program Files\WPS Office\12.1.0.14509\office6\wpp.exe'
                ]
            }
            
            possible_paths = office_paths.get(file_ext, [])
            for office_path in possible_paths:
                if os.path.exists(office_path):
                    print(f"尝试使用完整路径: {office_path}")
                    subprocess.Popen([office_path, file_path], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                    print(f"使用完整路径启动成功: {office_path}")
                    return True
                    
        except Exception as e3:
            print(f"使用完整路径Office程序打开失败: {e3}")
            
        # 最后尝试使用start命令
        try:
            print("尝试使用start命令...")
            subprocess.run(['start', '', file_path], 
                         shell=True, 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            print("start命令执行成功")
            return True
        except Exception as e4:
            print(f"使用start命令打开失败: {e4}")
            
        print("所有打开方式都失败了")
        return False
    
    def remove_duplicate_files(self, data):
        """移除重复文件记录，保留最新的"""
        file_dict = {}
        
        for item in data:
            file_name = item.get('文件名', '')
            if not file_name:
                continue
            
            # 如果文件已存在，比较时间戳
            if file_name in file_dict:
                existing_time = file_dict[file_name].get('处理时间', '')
                current_time = item.get('处理时间', '')
            
                # 保留时间较新的记录
                if current_time > existing_time:
                    file_dict[file_name] = item
            else:
                file_dict[file_name] = item
        
        return list(file_dict.values())
    
    def send_json_response(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def handle_download_file(self):
        """处理文件下载请求"""
        try:
            # 解析文件路径参数
            from urllib.parse import parse_qs, urlparse, unquote
            
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            file_path = query_params.get('path', [None])[0]
            
            if not file_path:
                self.send_error(400, "Missing file path parameter")
                return
            
            # URL解码文件路径
            file_path = unquote(file_path)
            
            # 处理Windows路径分隔符和空格问题
            file_path = file_path.replace('/', '\\')
            
            # 调试信息
            print(f"请求下载文件: {file_path}")
            print(f"文件是否存在: {os.path.exists(file_path)}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"文件不存在: {file_path}")
                
                # 尝试从JSON文件中查找文件路径
                json_file = Path('ai_organize_result.json')
                if json_file.exists():
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    except json.JSONDecodeError as e:
                        print(f"JSON文件格式错误，跳过文件查找: {e}")
                        data = []
                    except Exception as e:
                        print(f"读取JSON文件失败，跳过文件查找: {e}")
                        data = []
                    
                    # 查找匹配的文件
                    for item in data:
                        target_path = item.get('最终目标路径', '')
                        file_name = item.get('文件名', '')
                        
                        # 检查路径是否匹配
                        if (target_path == file_path or 
                            file_name in file_path or 
                            file_path in target_path):
                            
                            if target_path and os.path.exists(target_path):
                                file_path = target_path
                                print(f"从JSON中找到文件: {file_path}")
                                break
                
                # 如果仍然找不到，尝试不同的路径格式
                if not os.path.exists(file_path):
                    alt_path = file_path.replace('\\', '/')
                    if os.path.exists(alt_path):
                        file_path = alt_path
                        print(f"使用备用路径: {file_path}")
                    else:
                        # 如果文件确实不存在，返回404
                        self.send_response(404)
                        self.send_header('Content-Type', 'text/plain; charset=utf-8')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(f"File not found: {file_path}".encode('utf-8'))
                        return
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # 根据文件类型决定处理策略
            if self.should_preview_inline(file_ext):
                # 支持内联预览的文件类型
                self.handle_inline_preview(file_path, file_name, file_size)
            else:
                # 需要下载的文件类型
                self.handle_file_download(file_path, file_name, file_size)
                
        except Exception as e:
            print(f"下载文件时出错: {e}")
            # 返回简单的错误信息，避免编码问题
            try:
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_msg = f"Download failed: {str(e)}"
                self.wfile.write(error_msg.encode('utf-8'))
            except:
                # 如果还是有问题，发送最简单的错误信息
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Download failed")
    
    def should_preview_inline(self, file_ext):
        """判断文件是否应该内联预览"""
        # 支持内联预览的文件类型
        inline_types = {
            '.pdf', '.txt', '.html', '.htm', '.xml', '.json', '.csv',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
            '.mp4', '.webm', '.ogg', '.mp3', '.wav', '.flac'
        }
        return file_ext in inline_types
    
    def handle_inline_preview(self, file_path, file_name, file_size):
        """处理内联预览文件"""
        mime_type = self.get_mime_type(file_name)
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # 对于PDF文件，优化处理
        if file_ext == '.pdf':
            self.handle_pdf_preview(file_path, file_name, file_size)
            return
        
        # 其他文件类型保持原有处理方式
        safe_filename = f"file{file_ext}" if file_ext else "file"
        
        # 设置响应头 - 让浏览器直接预览文件
        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Disposition', f'inline; filename="{safe_filename}"')
        self.send_header('Content-Length', str(file_size))
        self.send_header('Access-Control-Allow-Origin', '*')
        # 添加缓存控制，提高PDF加载速度
        self.send_header('Cache-Control', 'public, max-age=3600')  # 缓存1小时
        self.end_headers()
        
        # 直接发送文件内容
        with open(file_path, 'rb') as f:
            self.wfile.write(f.read())
    
    def handle_pdf_preview(self, file_path, file_name, file_size):
        """专门处理PDF文件预览，优化性能"""
        try:
            # 检查是否支持Range请求（用于大文件分块传输）
            range_header = self.headers.get('Range')
            
            if range_header:
                # 处理Range请求，支持断点续传
                self.handle_pdf_range_request(file_path, file_name, file_size, range_header)
            else:
                # 完整文件请求
                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.send_header('Content-Disposition', f'inline; filename="{file_name}"')
                self.send_header('Content-Length', str(file_size))
                self.send_header('Accept-Ranges', 'bytes')  # 支持Range请求
                self.send_header('Access-Control-Allow-Origin', '*')
                # PDF文件缓存更长时间
                self.send_header('Cache-Control', 'public, max-age=7200')  # 缓存2小时
                self.end_headers()
                
                # 分块读取和发送，避免内存占用过大
                chunk_size = 1024 * 1024  # 1MB chunks
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()  # 立即发送数据
                        
        except Exception as e:
            print(f"PDF预览处理失败: {e}")
            # 降级到普通文件处理
            self.handle_file_download(file_path, file_name, file_size)
    
    def handle_pdf_range_request(self, file_path, file_name, file_size, range_header):
        """处理PDF文件的Range请求，支持断点续传"""
        try:
            # 解析Range头
            range_str = range_header.replace('bytes=', '')
            start, end = range_str.split('-')
            start = int(start) if start else 0
            end = int(end) if end else file_size - 1
            
            # 计算实际范围
            if end >= file_size:
                end = file_size - 1
            content_length = end - start + 1
            
            # 发送206 Partial Content响应
            self.send_response(206)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', f'inline; filename="{file_name}"')
            self.send_header('Content-Length', str(content_length))
            self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'public, max-age=7200')
            self.end_headers()
            
            # 发送指定范围的数据
            with open(file_path, 'rb') as f:
                f.seek(start)
                remaining = content_length
                chunk_size = 1024 * 1024  # 1MB chunks
                
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
                    remaining -= len(chunk)
                    
        except Exception as e:
            print(f"PDF Range请求处理失败: {e}")
            # 降级到完整文件响应
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', f'inline; filename="{file_name}"')
            self.send_header('Content-Length', str(file_size))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
    
    def handle_file_download(self, file_path, file_name, file_size):
        """处理文件下载"""
        mime_type = self.get_mime_type(file_name)
        file_ext = os.path.splitext(file_name)[1]
        
        # 使用原始文件名，而不是通用的"file"前缀
        # 对文件名进行URL编码，确保特殊字符能正确处理
        import urllib.parse
        safe_filename = urllib.parse.quote(file_name)
        
        # 设置响应头 - 强制下载文件
        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Disposition', f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{safe_filename}')
        self.send_header('Content-Length', str(file_size))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # 直接发送文件内容
        with open(file_path, 'rb') as f:
            self.wfile.write(f.read())
    
    def get_mime_type(self, filename):
        """根据文件扩展名获取MIME类型"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type
        
        # 常见文件类型的MIME类型映射
        mime_map = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain',
            '.rtf': 'application/rtf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed'
        }
        
        ext = os.path.splitext(filename)[1].lower()
        return mime_map.get(ext, 'application/octet-stream')
    
    def do_OPTIONS(self):
        """处理预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def start_local_server(port=80, bind_address="0.0.0.0"):
    """
    启动本地HTTP服务器
    
    Args:
        port (int): 服务器端口号，默认80（隐藏端口）
        bind_address (str): 绑定地址，默认0.0.0.0（所有网络接口）
    """
    try:
        # 确保在正确的目录下启动服务器
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        
        # 检查必要文件是否存在
        html_file = script_dir / 'viewer.html'
        fallback_html_file = script_dir / 'ai_result_viewer.html'
        json_file = script_dir / 'ai_organize_result.json'
        
        # 创建HTTP服务器
        handler = CustomHTTPRequestHandler
        
        # 尝试启动服务器
        with socketserver.TCPServer((bind_address, port), handler) as httpd:
            # 获取本机IP地址
            local_ip = get_local_ip()
            
            # 构建服务器URL
            if bind_address == "0.0.0.0":
                server_url = f"http://{local_ip}" if port == 80 else f"http://{local_ip}:{port}"
                localhost_url = f"http://localhost" if port == 80 else f"http://localhost:{port}"
            else:
                server_url = f"http://{bind_address}" if port == 80 else f"http://{bind_address}:{port}"
                localhost_url = server_url
            
            # 优先使用viewer.html，如果不存在则使用ai_result_viewer.html
            if html_file.exists():
                primary_html = 'viewer.html'
                primary_url = f"{server_url}/viewer.html"
                localhost_primary_url = f"{localhost_url}/viewer.html"
            elif fallback_html_file.exists():
                primary_html = 'ai_result_viewer.html'
                primary_url = f"{server_url}/ai_result_viewer.html"
                localhost_primary_url = f"{localhost_url}/ai_result_viewer.html"
                print(f"注意: 使用备用HTML文件 {fallback_html_file}")
            else:
                print(f"错误: 找不到HTML文件 viewer.html 或 ai_result_viewer.html")
                return False
            
            if not json_file.exists():
                print(f"警告: JSON文件 {json_file} 不存在，将显示空数据")
            
            print(f"服务器已启动 - 本机: {localhost_primary_url}")
            
            # 启动服务器后立即打开浏览器
            open_browser_with_urls(local_ip, port)
            
            # 启动服务器
            httpd.serve_forever()
            
    except OSError as e:
        if e.errno == 10048:  # 端口被占用
            print(f"错误: 端口 {port} 已被占用，尝试使用端口 {port + 1}")
            return start_local_server(port + 1, bind_address)
        else:
            print(f"启动服务器失败: {e}")
            return False
    except KeyboardInterrupt:
        print("\n服务器已停止")
        return True
    except Exception as e:
        print(f"服务器运行出错: {e}")
        return False

def main():
    """
    主函数
    """
    
    # 检查命令行参数
    port = 80  # 默认使用80端口，浏览器不显示端口号
    bind_address = "0.0.0.0"  # 默认绑定到所有网络接口
    
    # 解析命令行参数
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.isdigit():
            port = int(arg)
        elif arg in ["0.0.0.0", "localhost", "127.0.0.1"]:
            bind_address = arg
        else:
            print(f"未知参数: {arg}")
    
    # 检查服务器是否已经在运行
    if check_server_running(port):
        local_ip = get_local_ip()
        open_browser_with_urls(local_ip, port)
        return True
    
    # 启动服务器
    success = start_local_server(port, bind_address)
    
    if not success:
        print("\n服务器启动失败，请检查错误信息")
        input("按回车键退出...")
        sys.exit(1)

if __name__ == "__main__":
    main()