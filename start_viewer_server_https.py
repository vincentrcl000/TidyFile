#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI文件整理结果查看器 - HTTPS局域网服务器
支持HTTPS局域网访问，提供文件预览和下载功能
"""

import os
import sys
import json
import time
import socket
import webbrowser
import http.server
import socketserver
import subprocess
import threading
import ssl
import re
import psutil
import gc
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote, quote
import urllib.parse
import mimetypes
import hashlib
import tempfile
import shutil
from collections import defaultdict
from datetime import datetime, timedelta

# 进程名称设置已移至VBS启动脚本中
PROCESS_TITLE_SET = False

# 添加Windows COM支持
try:
    import win32com.client
    import pythoncom
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False
    print("警告: pywin32库未安装，Microsoft Office COM转换功能将不可用")

# 缓存目录
CACHE_DIR = Path("cache")
if not CACHE_DIR.exists():
    CACHE_DIR.mkdir(exist_ok=True)

# 文档转换缓存
DOC_CONVERSION_CACHE = {}

# 连接管理配置
CONNECTION_CONFIG = {
    'max_connections': 5,  # 最大并发连接数
    'connection_timeout': 300,  # 连接超时时间（秒）
    'keepalive_timeout': 60,  # Keep-Alive超时时间（秒）
    'cleanup_interval': 30,  # 清理间隔（秒）
    'max_memory_mb': 512,  # 最大内存使用（MB）
    'max_file_descriptors': 1000,  # 最大文件描述符数
}

# 连接状态跟踪
connection_stats = {
    'active_connections': 0,
    'total_connections': 0,
    'connection_history': defaultdict(int),
    'last_cleanup': time.time(),
    'memory_usage': 0,
    'file_descriptors': 0,
    'start_time': time.time()
}

class ConnectionManager:
    """连接管理器"""
    
    def __init__(self):
        self.active_connections = set()
        self.connection_times = {}
        self.lock = threading.Lock()
        self.cleanup_thread = None
        self.monitor_thread = None
        
    def add_connection(self, connection_id):
        """添加新连接"""
        with self.lock:
            self.active_connections.add(connection_id)
            self.connection_times[connection_id] = time.time()
            connection_stats['active_connections'] = len(self.active_connections)
            connection_stats['total_connections'] += 1
            
    def remove_connection(self, connection_id):
        """移除连接"""
        with self.lock:
            if connection_id in self.active_connections:
                self.active_connections.remove(connection_id)
            if connection_id in self.connection_times:
                del self.connection_times[connection_id]
            connection_stats['active_connections'] = len(self.active_connections)
            
    def cleanup_expired_connections(self):
        """清理过期连接"""
        current_time = time.time()
        expired_connections = []
        
        with self.lock:
            for conn_id, conn_time in self.connection_times.items():
                if current_time - conn_time > CONNECTION_CONFIG['connection_timeout']:
                    expired_connections.append(conn_id)
            
            for conn_id in expired_connections:
                self.remove_connection(conn_id)
                
        if expired_connections:
            print(f"清理了 {len(expired_connections)} 个过期连接")
            
    def get_stats(self):
        """获取连接统计信息"""
        with self.lock:
            return {
                'active_connections': len(self.active_connections),
                'total_connections': connection_stats['total_connections'],
                'connection_times': len(self.connection_times)
            }
            
    def start_monitoring(self):
        """启动监控线程"""
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        
        self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self.monitor_thread.start()
        
    def _cleanup_worker(self):
        """清理工作线程"""
        while True:
            try:
                time.sleep(CONNECTION_CONFIG['cleanup_interval'])
                self.cleanup_expired_connections()
                self._check_resource_limits()
            except Exception as e:
                print(f"清理线程异常: {e}")
                
    def _monitor_worker(self):
        """监控工作线程"""
        while True:
            try:
                time.sleep(10)  # 每10秒监控一次
                self._update_resource_stats()
            except Exception as e:
                print(f"监控线程异常: {e}")
                
    def _update_resource_stats(self):
        """更新资源统计"""
        try:
            # 更新内存使用
            process = psutil.Process()
            memory_info = process.memory_info()
            connection_stats['memory_usage'] = memory_info.rss / 1024 / 1024  # MB
            
            # 更新文件描述符数量
            connection_stats['file_descriptors'] = len(process.open_files())
            
        except Exception as e:
            print(f"更新资源统计失败: {e}")
            
    def _check_resource_limits(self):
        """检查资源限制"""
        try:
            # 检查内存使用
            if connection_stats['memory_usage'] > CONNECTION_CONFIG['max_memory_mb']:
                print(f"内存使用超过限制: {connection_stats['memory_usage']:.1f}MB > {CONNECTION_CONFIG['max_memory_mb']}MB")
                gc.collect()  # 强制垃圾回收
                
            # 检查文件描述符
            if connection_stats['file_descriptors'] > CONNECTION_CONFIG['max_file_descriptors']:
                print(f"文件描述符超过限制: {connection_stats['file_descriptors']} > {CONNECTION_CONFIG['max_file_descriptors']}")
                
            # 检查连接数
            if len(self.active_connections) > CONNECTION_CONFIG['max_connections']:
                print(f"连接数超过限制: {len(self.active_connections)} > {CONNECTION_CONFIG['max_connections']}")
                # 强制清理最旧的连接
                self._force_cleanup_oldest_connections()
                
        except Exception as e:
            print(f"检查资源限制失败: {e}")
            
    def _force_cleanup_oldest_connections(self):
        """强制清理最旧的连接"""
        with self.lock:
            if len(self.connection_times) > CONNECTION_CONFIG['max_connections']:
                # 按时间排序，保留最新的连接
                sorted_connections = sorted(
                    self.connection_times.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )
                
                # 移除最旧的连接
                connections_to_remove = sorted_connections[CONNECTION_CONFIG['max_connections']:]
                for conn_id, _ in connections_to_remove:
                    self.remove_connection(conn_id)
                    
                print(f"强制清理了 {len(connections_to_remove)} 个旧连接")

# 全局连接管理器实例
connection_manager = ConnectionManager()

def get_cache_key(file_path):
    """生成缓存键"""
    file_stat = os.stat(file_path)
    return hashlib.md5(f"{file_path}_{file_stat.st_mtime}_{file_stat.st_size}".encode()).hexdigest()

def convert_office_to_pdf_advanced(file_path, cache_key=None):
    """Office文件转PDF，仅使用win32com，失败则返回None"""
    if cache_key is None:
        cache_key = get_cache_key(file_path)
    
    # 检查缓存
    cache_file = CACHE_DIR / f"{cache_key}.pdf"
    if cache_file.exists():
        print(f"使用缓存的PDF文件: {cache_file}")
        return str(cache_file)
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # 只尝试win32com转换
    try:
        print(f"尝试使用 Microsoft Office COM 转换文件: {file_path}")
        result = convert_with_msoffice_com(file_path, cache_file, file_ext)
        if result:
            print(f"使用 Microsoft Office COM 成功转换文件")
            return str(cache_file)
    except Exception as e:
        print(f"Microsoft Office COM 转换失败: {e}")
    
    print("Office转换失败，将使用原始文件")
    return None

def convert_with_msoffice_com(file_path, cache_file, file_ext):
    """使用Microsoft Office COM接口转换（按照用户成功示例优化）"""
    if not WIN32COM_AVAILABLE:
        raise Exception("pywin32库不可用")
    
    # 确保文件路径是绝对路径
    file_path = os.path.abspath(file_path)
    output_path = os.path.abspath(str(cache_file))
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    print(f"输入文件路径: {file_path}")
    print(f"输出文件路径: {output_path}")
    print(f"输出目录: {output_dir}")
    print(f"输出目录是否存在: {os.path.exists(output_dir)}")
    
    # 根据文件类型选择应用程序
    ext = file_ext.lower()
    app = None
    
    try:
        # 首先尝试强制关闭可能存在的Word实例
        if ext in ['.doc', '.docx']:
            try:
                import subprocess
                subprocess.run(['taskkill', '/F', '/IM', 'WINWORD.EXE'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NO_WINDOW)
                print("已强制关闭现有Word实例")
            except:
                pass
        
        if ext in ['.doc', '.docx']:
            print(f"使用Word转换: {file_path}")
            app = win32com.client.Dispatch('Word.Application')
            app.Visible = False
            doc = app.Documents.Open(file_path)
            doc.SaveAs(output_path, FileFormat=17)  # 17 = PDF
            doc.Close()
            
        elif ext in ['.xls', '.xlsx']:
            print(f"使用Excel转换: {file_path}")
            app = win32com.client.Dispatch('Excel.Application')
            app.Visible = False
            wb = app.Workbooks.Open(file_path)
            wb.ExportAsFixedFormat(0, output_path)  # 0 = PDF
            wb.Close()
            
        elif ext in ['.ppt', '.pptx']:
            print(f"使用PowerPoint转换: {file_path}")
            app = win32com.client.Dispatch('PowerPoint.Application')
            app.Visible = False
            ppt = app.Presentations.Open(file_path, WithWindow=False)
            ppt.SaveAs(output_path, FileFormat=32)  # 32 = PDF
            ppt.Close()
            
        else:
            raise Exception(f"不支持的文件类型: {file_ext}")
        
        # 确保应用程序正确退出
        if app:
            app.Quit()
        
        # 验证输出文件是否存在
        if os.path.exists(output_path):
            print(f"转换成功: {output_path}")
            return True
        else:
            raise Exception("转换后未找到输出文件")
        
    except Exception as e:
        print(f"Microsoft Office COM转换失败: {e}")
        # 尝试清理应用程序实例
        try:
            if app:
                app.Quit()
        except:
            pass
        
        # 如果失败，尝试使用备用方法
        try:
            print("尝试使用备用转换方法...")
            return convert_with_fallback_method(file_path, cache_file, file_ext)
        except Exception as fallback_error:
            print(f"备用转换方法也失败: {fallback_error}")
            raise

def convert_with_fallback_method(file_path, cache_file, file_ext):
    """备用转换方法：使用不同的COM调用方式"""
    try:
        import win32com.client as win32
        
        # 确保文件路径是绝对路径
        file_path = os.path.abspath(file_path)
        output_path = os.path.abspath(str(cache_file))
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        print(f"备用方法 - 输入文件路径: {file_path}")
        print(f"备用方法 - 输出文件路径: {output_path}")
        
        # 根据文件类型选择应用程序
        ext = file_ext.lower()
        app = None
        
        if ext in ['.doc', '.docx']:
            print(f"备用方法：使用Word转换: {file_path}")
            app = win32.Dispatch('Word.Application')
            doc = app.Documents.Open(file_path)
            doc.SaveAs(output_path, FileFormat=17)  # 17 = PDF
            doc.Close()
            
        elif ext in ['.xls', '.xlsx']:
            print(f"备用方法：使用Excel转换: {file_path}")
            app = win32.Dispatch('Excel.Application')
            wb = app.Workbooks.Open(file_path)
            wb.ExportAsFixedFormat(0, output_path)  # 0 = PDF
            wb.Close()
            
        elif ext in ['.ppt', '.pptx']:
            print(f"备用方法：使用PowerPoint转换: {file_path}")
            app = win32.Dispatch('PowerPoint.Application')
            ppt = app.Presentations.Open(file_path, WithWindow=False)
            ppt.SaveAs(output_path, FileFormat=32)  # 32 = PDF
            ppt.Close()
            
        else:
            raise Exception(f"不支持的文件类型: {file_ext}")
        
        # 确保应用程序正确退出
        if app:
            app.Quit()
        
        # 验证输出文件是否存在
        if os.path.exists(output_path):
            print(f"备用方法转换成功: {output_path}")
            return True
        else:
            raise Exception("备用方法转换后未找到输出文件")
        
    except Exception as e:
        print(f"备用转换方法失败: {e}")
        raise



def get_local_ip():
    """获取本机IP地址"""
    try:
        # 创建一个UDP套接字
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个外部地址（不需要真实连接）
        s.connect(("8.8.8.8", 80))
        # 获取本地IP
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def check_server_running(port=443):
    """检查服务器是否已在运行"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

def open_browser_with_urls(local_ip, port=443):
    """打开浏览器显示访问地址"""
    print(f"\n=== 服务器启动成功 ===")
    print(f"本机访问: https://localhost/viewer.html")
    print(f"局域网访问: https://{local_ip}/viewer.html")
    print(f"按 Ctrl+C 停止服务器")
    print("=" * 50)

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    自定义HTTP请求处理器，支持清理重复文件的API
    """
    
    def setup(self):
        """设置连接，添加连接管理"""
        super().setup()
        # 设置连接超时
        self.connection.settimeout(CONNECTION_CONFIG['connection_timeout'])
        
        # 生成连接ID并添加到管理器
        self.connection_id = f"{self.client_address[0]}:{self.client_address[1]}:{time.time()}"
        connection_manager.add_connection(self.connection_id)
        
        print(f"新连接建立: {self.connection_id}")
    
    def finish(self):
        """连接结束，清理资源"""
        try:
            # 从连接管理器中移除
            if hasattr(self, 'connection_id'):
                connection_manager.remove_connection(self.connection_id)
                print(f"连接结束: {self.connection_id}")
        except Exception as e:
            print(f"清理连接时出错: {e}")
        finally:
            super().finish()
    
    def end_headers(self):
        """重写end_headers方法，添加缓存控制头和CORS头，避免重复头"""
        # 为HTML文件添加缓存控制头，强制浏览器重新加载
        if self.path.endswith('.html'):
            if 'Cache-Control' not in self._headers_buffer:
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            if 'Pragma' not in self._headers_buffer:
                self.send_header('Pragma', 'no-cache')
            if 'Expires' not in self._headers_buffer:
                self.send_header('Expires', '0')
        
        # 只有在没有设置CORS头的情况下才添加
        if 'Access-Control-Allow-Origin' not in self._headers_buffer:
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, HEAD, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        
        # 调用父类的end_headers，但不重复设置已存在的头
        super().end_headers()
    
    def get_client_info(self):
        """获取客户端信息"""
        client_ip = self.client_address[0]
        
        # 本地访问：只有127.0.0.1, localhost, ::1
        is_local_access = client_ip in ['127.0.0.1', 'localhost', '::1']
        
        # 局域网访问：192.168.x.x, 10.x.x.x, 172.16-31.x.x
        is_local_network = (
            client_ip.startswith('192.168.') or 
            client_ip.startswith('10.') or 
            client_ip.startswith(('172.16.', '172.17.', '172.18.', '172.19.', '172.20.', 
                                 '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', 
                                 '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.'))
        )
        
        # 远程访问：既不是本地访问也不是局域网访问
        is_remote = not (is_local_access or is_local_network)
        
        print(f"客户端IP: {client_ip}, 本地访问: {is_local_access}, 局域网访问: {is_local_network}, 远程访问: {is_remote}")
        
        return {
            'ip': client_ip,
            'is_local': is_local_access,
            'is_local_network': is_local_network,
            'is_remote': is_remote
        }
    
    def do_POST(self):
        """处理POST请求"""
        client_info = self.get_client_info()
        
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
        elif self.path == '/api/connection-stats':
            self.handle_connection_stats()
        elif self.path == '/api/open-file':
            # 根据客户端类型使用不同的处理方法
            if client_info['is_local']:
                print("本地访问，使用本地文件打开方法")
                self.handle_local_open_file()
            else:
                print("非本地访问，使用远程文件处理方法")
                self.handle_remote_open_file()
        else:
            self.send_error(404, "API endpoint not found")
    
    def do_GET(self):
        """处理GET请求"""
        client_info = self.get_client_info()
        
        if self.path.startswith('/api/download-file'):
            # 根据客户端类型使用不同的处理方法
            if client_info['is_local']:
                print("本地访问，使用本地文件下载方法")
                self.handle_local_download_file()
            else:
                print("非本地访问，使用远程文件下载方法")
                self.handle_remote_download_file()
        elif self.path == '/api/heartbeat':
            self.handle_heartbeat()
        elif self.path == '/api/connection-stats':
            self.handle_connection_stats()
        else:
            super().do_GET()
    
    def do_HEAD(self):
        """处理HEAD请求"""
        client_info = self.get_client_info()
        
        if self.path.startswith('/api/download-file'):
            # 根据客户端类型使用不同的处理方法
            if client_info['is_local']:
                print("本地访问，使用本地文件下载方法")
                self.handle_local_download_file()
            else:
                print("非本地访问，使用远程文件下载方法")
                self.handle_remote_download_file()
        elif self.path == '/api/heartbeat':
            self.handle_heartbeat()
        elif self.path == '/api/connection-stats':
            self.handle_connection_stats()
        else:
            super().do_HEAD()

    def handle_clean_duplicates(self):
        """处理清理重复文件的请求"""
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
            
            # 只检查文件路径
            checked_data = self.check_file_paths_only(data)
            
            # 统计检查结果
            total_files = len(checked_data)
            valid_paths = sum(1 for item in checked_data if os.path.exists(item.get('最终目标路径', '')))
            not_found = total_files - valid_paths
            
            self.send_json_response({
                'success': True,
                'message': f'路径检查完成',
                'total_files': total_files,
                'valid_paths': valid_paths,
                'not_found': not_found
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
            updated_paths = sum(1 for item in updated_data if item.get('路径已更新', False))
            not_found = total_files - valid_paths - updated_paths
            
            self.send_json_response({
                'success': True,
                'message': f'路径搜索和更新完成',
                'total_files': total_files,
                'valid_paths': valid_paths,
                'updated_paths': updated_paths,
                'not_found': not_found
            })
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'路径搜索和更新失败: {str(e)}'})

    def handle_shutdown(self):
        """处理服务器关闭请求"""
        try:
            self.send_json_response({'success': True, 'message': '服务器将在3秒后关闭'})
            
            # 延迟关闭服务器
            def delayed_shutdown():
                time.sleep(3)
                os._exit(0)
            
            threading.Thread(target=delayed_shutdown, daemon=True).start()
            
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'关闭失败: {str(e)}'})

    def handle_heartbeat(self):
        """处理心跳请求"""
        try:
            # 更新连接时间
            if hasattr(self, 'connection_id'):
                with connection_manager.lock:
                    if self.connection_id in connection_manager.connection_times:
                        connection_manager.connection_times[self.connection_id] = time.time()
            
            # 获取连接统计信息
            stats = connection_manager.get_stats()
            resource_stats = {
                'memory_usage_mb': round(connection_stats['memory_usage'], 2),
                'file_descriptors': connection_stats['file_descriptors'],
                'active_connections': stats['active_connections'],
                'total_connections': stats['total_connections']
            }
            
            self.send_json_response({
                'success': True, 
                'message': '服务器运行正常', 
                'timestamp': time.time(),
                'stats': resource_stats
            })
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'心跳检查失败: {str(e)}'})

    def handle_connection_stats(self):
        """处理连接统计请求"""
        try:
            stats = connection_manager.get_stats()
            resource_stats = {
                'memory_usage_mb': round(connection_stats['memory_usage'], 2),
                'file_descriptors': connection_stats['file_descriptors'],
                'active_connections': stats['active_connections'],
                'total_connections': stats['total_connections'],
                'connection_times_count': stats['connection_times'],
                'uptime_seconds': time.time() - connection_stats.get('start_time', time.time()),
                'last_cleanup': connection_stats['last_cleanup']
            }
            
            self.send_json_response({
                'success': True,
                'stats': resource_stats,
                'config': CONNECTION_CONFIG
            })
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'获取统计信息失败: {str(e)}'})

    def handle_local_open_file(self):
        """处理本地文件打开请求"""
        try:
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # 解析JSON数据
            try:
                data = json.loads(post_data)
                file_path = data.get('filePath', '')
            except json.JSONDecodeError:
                self.send_json_response({'success': False, 'error': '无效的JSON数据'})
                return
            
            if not file_path:
                self.send_json_response({'success': False, 'error': '文件路径不能为空'})
                return
            
            print(f"收到打开文件请求: {file_path}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                self.send_json_response({'success': False, 'error': f'文件不存在: {file_path}'})
                return
            
            # 获取文件信息
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            print(f"文件信息: 名称={file_name}, 扩展名={file_ext}")
            
            # 在服务器上打开文件
            success = self.open_file_on_server(file_path, file_ext, file_name)
            
            if success:
                self.send_json_response({
                    'success': True, 
                    'message': f'文件 "{file_name}" 正在使用系统默认程序打开'
                })
            else:
                self.send_json_response({
                    'success': False, 
                    'error': f'无法找到合适的程序打开 {file_name}'
                })
                
        except Exception as e:
            print(f"打开文件异常: {e}")
            self.send_json_response({'success': False, 'error': f'打开文件失败: {str(e)}'})

    def handle_remote_open_file(self):
        """处理远程文件打开请求"""
        try:
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # 解析JSON数据
            try:
                data = json.loads(post_data)
                file_path = data.get('filePath', '')
            except json.JSONDecodeError:
                self.send_json_response({'success': False, 'error': '无效的JSON数据'})
                return
            
            if not file_path:
                self.send_json_response({'success': False, 'error': '文件路径不能为空'})
                return
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                self.send_json_response({'success': False, 'error': f'文件不存在: {file_path}'})
                return
            
            # 获取文件信息
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # 远程访问：返回下载链接
            download_url = f"/api/download-file?path={quote(file_path)}"
            
            self.send_json_response({
                'success': True,
                'message': f'文件 "{file_name}" 准备下载',
                'download_url': download_url,
                'file_name': file_name
            })
            
        except Exception as e:
            self.send_json_response({'success': False, 'error': f'处理文件请求失败: {str(e)}'})

    def handle_local_download_file(self):
        """处理本地文件下载请求 - 返回JSON响应"""
        try:
            # 解析文件路径参数
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
            print(f"本地访问 - 原始请求路径: {self.path}")
            print(f"本地访问 - 解析后的文件路径: {file_path}")
            print(f"本地访问 - 文件是否存在: {os.path.exists(file_path)}")
            
            # 尝试规范化路径
            try:
                normalized_path = os.path.normpath(file_path)
                print(f"本地访问 - 规范化后的路径: {normalized_path}")
                print(f"本地访问 - 规范化路径是否存在: {os.path.exists(normalized_path)}")
                if os.path.exists(normalized_path):
                    file_path = normalized_path
            except Exception as norm_error:
                print(f"本地访问 - 路径规范化失败: {norm_error}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"本地访问 - 文件不存在: {file_path}")
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                if self.command != 'HEAD':
                    self.wfile.write(f"File not found: {file_path}".encode('utf-8'))
                return
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            print(f"本地访问 - 文件信息: 名称={file_name}, 扩展名={file_ext}, 大小={file_size}")
            
            # 本地访问：不进行Office文档转PDF，直接处理
            print(f"本地访问Office文档，不进行PDF转换，直接处理: {file_path}")
            
            # 对于HEAD请求，只返回响应头
            if self.command == 'HEAD':
                mime_type = self.get_mime_type(file_name)
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', str(file_size))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'public, max-age=3600')
                self.end_headers()
                return
            
            # 根据文件类型决定处理策略
            if self.should_preview_inline(file_ext):
                # 支持内联预览的文件类型
                self.handle_inline_preview(file_path, file_name, file_size)
            else:
                # 不支持预览的文件类型，直接下载
                self.handle_file_download(file_path, file_name, file_size)
                
        except Exception as e:
            print(f"本地访问 - 处理文件下载请求时出错: {str(e)}")
            self.send_error(500, f"Internal Server Error: {str(e)}")

    def handle_remote_download_file(self):
        """处理远程访问的文件下载请求 - 先转换PDF，失败才下载"""
        try:
            # 解析文件路径参数
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
            print(f"远程访问 - 原始请求路径: {self.path}")
            print(f"远程访问 - 解析后的文件路径: {file_path}")
            print(f"远程访问 - 文件是否存在: {os.path.exists(file_path)}")
            
            # 尝试规范化路径
            try:
                normalized_path = os.path.normpath(file_path)
                print(f"远程访问 - 规范化后的路径: {normalized_path}")
                print(f"远程访问 - 规范化路径是否存在: {os.path.exists(normalized_path)}")
                if os.path.exists(normalized_path):
                    file_path = normalized_path
            except Exception as norm_error:
                print(f"远程访问 - 路径规范化失败: {norm_error}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"远程访问 - 文件不存在: {file_path}")
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                if self.command != 'HEAD':
                    self.wfile.write(f"File not found: {file_path}".encode('utf-8'))
                return
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            print(f"远程访问 - 文件信息: 名称={file_name}, 扩展名={file_ext}, 大小={file_size}")
            
            # 远程访问：先尝试Office文档转PDF，成功则使用PDF预览，失败才下载原始文件
            if file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
                print(f"远程访问检测到Office文档，尝试转换为PDF: {file_path}")
                pdf_path = convert_office_to_pdf_advanced(file_path)
                if pdf_path and os.path.exists(pdf_path):
                    print(f"✅ Office文档转换成功，使用PDF预览: {pdf_path}")
                    # 使用PDF预览方式处理
                    self.handle_pdf_preview(pdf_path, os.path.basename(pdf_path), os.path.getsize(pdf_path))
                    return
                else:
                    print(f"❌ Office文档转换失败，下载原始文件: {file_path}")
                    # 转换失败，下载原始文件
                    self.handle_file_download(file_path, file_name, file_size)
                    return
            
            # 对于HEAD请求，只返回响应头
            if self.command == 'HEAD':
                mime_type = self.get_mime_type(file_name)
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', str(file_size))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'public, max-age=3600')
                self.end_headers()
                return
            
            # 根据文件类型决定处理策略
            if self.should_preview_inline(file_ext):
                # 支持内联预览的文件类型
                self.handle_inline_preview(file_path, file_name, file_size)
            else:
                # 不支持预览的文件类型，直接下载
                self.handle_file_download(file_path, file_name, file_size)
                
        except Exception as e:
            print(f"远程访问 - 处理文件下载请求时出错: {str(e)}")
            self.send_error(500, f"Internal Server Error: {str(e)}")

    def send_json_response(self, data):
        """发送JSON响应"""
        try:
            response = json.dumps(data, ensure_ascii=False)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
        except Exception as e:
            print(f"发送JSON响应失败: {e}")

    def open_file_on_server(self, file_path, file_ext, file_name):
        """在服务器上打开文件"""
        try:
            print(f"检测到Windows系统")
            
            # 检查是否为Office文件
            if self.is_office_file(file_ext):
                print(f"检测到Office文件: {file_ext}")
                return self.open_office_file_windows(file_path, file_ext)
            else:
                print(f"尝试打开Office文件: {file_path}")
                # 使用系统默认程序打开
                print("尝试使用系统默认程序打开...")
                result = os.startfile(file_path)
                print("系统默认程序打开成功")
                return True
                
        except Exception as e:
            print(f"打开文件异常: {e}")
            return False

    def is_office_file(self, file_ext):
        """判断是否为Office文件"""
        return file_ext.lower() in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']

    def open_office_file_windows(self, file_path, file_ext):
        """在Windows上打开Office文件"""
        try:
            print(f"尝试打开Office文件: {file_path}")
            
            # 使用系统默认程序打开
            print("尝试使用系统默认程序打开...")
            result = os.startfile(file_path)
            print("系统默认程序打开成功")
            return True
            
        except Exception as e:
            print(f"Office文件打开结果: {e}")
            return False

    def should_preview_inline(self, file_ext):
        """判断是否应该内联预览"""
        preview_extensions = ['.pdf', '.txt', '.html', '.htm', '.css', '.js', '.json', '.xml', '.svg']
        return file_ext.lower() in preview_extensions

    def handle_inline_preview(self, file_path, file_name, file_size):
        """处理内联预览"""
        try:
            mime_type = self.get_mime_type(file_name)
            
            # 特殊处理PDF文件
            if file_name.lower().endswith('.pdf'):
                self.handle_pdf_preview(file_path, file_name, file_size)
                return
            
            # 其他文件类型
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(file_size))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'public, max-age=3600')
            self.end_headers()
            
            # 发送文件内容
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
                
        except Exception as e:
            print(f"内联预览失败: {e}")
            self.send_error(500, f"Preview failed: {str(e)}")

    def handle_pdf_preview(self, file_path, file_name, file_size):
        """处理PDF预览"""
        try:
            # 检查是否有Range请求
            range_header = self.headers.get('Range')
            if range_header:
                self.handle_pdf_range_request(file_path, file_name, file_size, range_header)
                return
            
            # 完整文件请求
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Length', str(file_size))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'public, max-age=3600')
            self.end_headers()
            
            # 发送文件内容
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
                
        except Exception as e:
            print(f"PDF预览失败: {e}")
            self.send_error(500, f"PDF preview failed: {str(e)}")

    def handle_pdf_range_request(self, file_path, file_name, file_size, range_header):
        """处理PDF范围请求"""
        try:
            # 解析Range头
            range_match = re.match(r'bytes=(\d+)-(\d+)?', range_header)
            if not range_match:
                self.send_error(400, "Invalid Range header")
                return
            
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            
            # 验证范围
            if start >= file_size or end >= file_size or start > end:
                self.send_error(416, "Requested range not satisfiable")
                return
            
            # 计算内容长度
            content_length = end - start + 1
            
            # 发送206响应
            self.send_response(206)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Length', str(content_length))
            self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 发送指定范围的内容
            with open(file_path, 'rb') as f:
                f.seek(start)
                self.wfile.write(f.read(content_length))
                
        except Exception as e:
            print(f"PDF范围请求失败: {e}")
            self.send_error(500, f"Range request failed: {str(e)}")

    def handle_file_download(self, file_path, file_name, file_size):
        """处理文件下载"""
        try:
            mime_type = self.get_mime_type(file_name)
            
            # 对文件名进行URL编码，避免编码错误
            safe_filename = urllib.parse.quote(file_name)
            
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(file_size))
            self.send_header('Content-Disposition', f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{safe_filename}')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'public, max-age=3600')
            self.end_headers()
            
            # 发送文件内容
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
                
        except Exception as e:
            print(f"文件下载失败: {e}")
            # 使用简单的错误信息，避免编码问题
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

    def get_mime_type(self, filename):
        """获取文件的MIME类型"""
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        return mime_type

    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def remove_duplicate_files(self, data):
        """移除重复文件，保留最新的"""
        if not isinstance(data, list):
            return data
        
        # 按文件名分组
        file_groups = {}
        for item in data:
            if isinstance(item, dict) and '文件名' in item:
                file_name = item['文件名']
                if file_name not in file_groups:
                    file_groups[file_name] = []
                file_groups[file_name].append(item)
        
        # 保留每个文件的最新记录
        cleaned_data = []
        for file_name, items in file_groups.items():
            if len(items) == 1:
                cleaned_data.append(items[0])
            else:
                # 多个记录，保留最新的
                latest_item = max(items, key=lambda x: x.get('修改时间', ''))
                cleaned_data.append(latest_item)
        
        return cleaned_data

    def check_and_fix_file_paths(self, data):
        """检查并修复文件路径"""
        if not isinstance(data, list):
            return data
        
        for item in data:
            if isinstance(item, dict) and '最终目标路径' in item:
                original_path = item['最终目标路径']
                
                # 检查路径是否存在
                if not os.path.exists(original_path):
                    # 尝试修复路径
                    fixed_path = self.search_file_in_system(os.path.basename(original_path))
                    if fixed_path:
                        item['最终目标路径'] = fixed_path
                        item['路径已修复'] = True
                    else:
                        item['路径已修复'] = False
                else:
                    item['路径已修复'] = False
        
        return data

    def check_file_paths_only(self, data):
        """只检查文件路径，不修复"""
        if not isinstance(data, list):
            return data
        
        for item in data:
            if isinstance(item, dict) and '最终目标路径' in item:
                original_path = item['最终目标路径']
                item['路径存在'] = os.path.exists(original_path)
        
        return data

    def search_and_update_file_paths(self, data):
        """搜索并更新文件路径"""
        if not isinstance(data, list):
            return data
        
        for item in data:
            if isinstance(item, dict) and '最终目标路径' in item:
                original_path = item['最终目标路径']
                
                # 检查路径是否存在
                if not os.path.exists(original_path):
                    # 搜索文件
                    found_path = self.search_file_in_system(os.path.basename(original_path))
                    if found_path:
                        item['最终目标路径'] = found_path
                        item['路径已更新'] = True
                    else:
                        item['路径已更新'] = False
                else:
                    item['路径已更新'] = False
        
        return data

    def search_file_in_system(self, file_name):
        """在系统中搜索文件"""
        # 尝试多种搜索方法
        search_methods = [
            self.search_with_windows_api,
            self.search_c_drive_user_dirs,
            self.fallback_search
        ]
        
        for method in search_methods:
            try:
                result = method(file_name)
                if result:
                    return result
            except Exception as e:
                print(f"搜索方法 {method.__name__} 失败: {e}")
                continue
        
        return None

    def search_with_windows_api(self, file_name):
        """使用Windows API搜索文件"""
        try:
            import subprocess
            # 使用dir命令搜索
            cmd = f'dir /s /b "{file_name}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip() and os.path.exists(line.strip()):
                        return line.strip()
        except Exception as e:
            print(f"Windows API搜索失败: {e}")
        
        return None

    def search_c_drive_user_dirs(self, file_name):
        """在C盘用户目录中搜索"""
        try:
            user_dirs = [
                os.path.expanduser('~'),
                os.path.join('C:', 'Users'),
                os.path.join('C:', 'Documents and Settings')
            ]
            
            for user_dir in user_dirs:
                if os.path.exists(user_dir):
                    result = self.search_file_recursive(user_dir, file_name)
                    if result:
                        return result
        except Exception as e:
            print(f"用户目录搜索失败: {e}")
        
        return None

    def fallback_search(self, file_name):
        """备用搜索方法"""
        try:
            # 搜索常见目录
            common_dirs = [
                'C:\\',
                'D:\\',
                'E:\\',
                'F:\\'
            ]
            
            for drive in common_dirs:
                if os.path.exists(drive):
                    result = self.search_file_recursive(drive, file_name, max_depth=2)
                    if result:
                        return result
        except Exception as e:
            print(f"备用搜索失败: {e}")
        
        return None

    def search_c_drive_user_dirs_fallback(self, file_name):
        """在C盘用户目录中搜索（备用方法）"""
        try:
            user_dirs = [
                os.path.expanduser('~'),
                os.path.join('C:', 'Users'),
                os.path.join('C:', 'Documents and Settings')
            ]
            
            for user_dir in user_dirs:
                if os.path.exists(user_dir):
                    result = self.search_file_recursive(user_dir, file_name, max_depth=3)
                    if result:
                        return result
        except Exception as e:
            print(f"用户目录备用搜索失败: {e}")
        
        return None

    def search_file_recursive(self, directory, file_name, max_depth=3):
        """递归搜索文件"""
        try:
            for root, dirs, files in os.walk(directory):
                # 检查深度
                depth = root[len(directory):].count(os.sep)
                if depth > max_depth:
                    continue
                
                for file in files:
                    if file == file_name:
                        full_path = os.path.join(root, file)
                        if os.path.exists(full_path):
                            return full_path
        except Exception as e:
            print(f"递归搜索失败: {e}")
        
        return None

def start_https_server(port=443, bind_address="0.0.0.0"):
    """启动HTTPS服务器"""
    try:
        # 创建自签名证书
        cert_file = "server.crt"
        key_file = "server.key"
        
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            print("生成自签名SSL证书...")
            generate_self_signed_cert(cert_file, key_file)
        
        # 创建服务器
        handler = CustomHTTPRequestHandler
        
        # 配置服务器参数
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        httpd = socketserver.ThreadingTCPServer((bind_address, port), handler)
        
        # 设置连接超时
        httpd.timeout = CONNECTION_CONFIG['keepalive_timeout']
        
        # 包装为HTTPS
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        
        # 启动连接管理器监控
        print("启动连接管理器...")
        connection_manager.start_monitoring()
        
        print(f"HTTPS服务器已启动 - 端口: {port}")
        print(f"连接配置: 最大连接数={CONNECTION_CONFIG['max_connections']}, 超时={CONNECTION_CONFIG['connection_timeout']}秒")
        print(f"本机: https://localhost/viewer.html")
        
        local_ip = get_local_ip()
        print(f"局域网: https://{local_ip}/viewer.html")
        
        # 在新线程中打开浏览器
        threading.Timer(1.0, lambda: open_browser_with_urls(local_ip, port)).start()
        
        # 启动服务器
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动HTTPS服务器失败: {e}")
        print("尝试使用HTTP服务器...")
        start_http_server(port, bind_address)

def generate_self_signed_cert(cert_file, key_file):
    """生成自签名SSL证书"""
    try:
        # 使用OpenSSL生成证书
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:4096", 
            "-keyout", key_file, "-out", cert_file, "-days", "365", 
            "-nodes", "-subj", "/C=CN/ST=Beijing/L=Beijing/O=Local/CN=localhost"
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        print("SSL证书生成成功")
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("OpenSSL不可用，使用Python生成证书...")
        generate_python_cert(cert_file, key_file)

def generate_python_cert(cert_file, key_file):
    """使用Python生成自签名证书"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from datetime import datetime, timedelta
        import ipaddress
        
        # 生成私钥
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # 创建证书
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Local"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # 保存私钥
        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # 保存证书
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        print("Python SSL证书生成成功")
        
    except ImportError:
        print("cryptography库不可用，无法生成SSL证书")
        print("请安装: pip install cryptography")
        sys.exit(1)

def start_http_server(port=80, bind_address="0.0.0.0"):
    """启动HTTP服务器（备用方案）"""
    try:
        handler = CustomHTTPRequestHandler
        
        # 配置服务器参数
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        httpd = socketserver.ThreadingTCPServer((bind_address, port), handler)
        
        # 设置连接超时
        httpd.timeout = CONNECTION_CONFIG['keepalive_timeout']
        
        # 启动连接管理器监控
        print("启动连接管理器...")
        connection_manager.start_monitoring()
        
        print(f"HTTP服务器已启动 - 端口: {port}")
        print(f"连接配置: 最大连接数={CONNECTION_CONFIG['max_connections']}, 超时={CONNECTION_CONFIG['connection_timeout']}秒")
        print(f"本机: http://localhost/viewer.html")
        
        local_ip = get_local_ip()
        print(f"局域网: http://{local_ip}/viewer.html")
        
        # 在新线程中打开浏览器
        threading.Timer(1.0, lambda: open_browser_with_urls(local_ip, port)).start()
        
        # 启动服务器
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动HTTP服务器失败: {e}")

def main():
    """主函数"""
    print("AI文件整理结果查看器 - HTTPS版本")
    print("=" * 50)
    
    # 检查端口是否被占用
    port = 443
    if check_server_running(port):
        print(f"端口 {port} 已被占用，尝试使用端口 8443...")
        port = 8443
        if check_server_running(port):
            print(f"端口 {port} 也被占用，请手动停止占用端口的程序")
            return
    
    try:
        # 启动HTTPS服务器
        start_https_server(port)
    except Exception as e:
        print(f"HTTPS服务器启动失败: {e}")
        print("尝试启动HTTP服务器...")
        start_http_server(80)

if __name__ == "__main__":
    main() 