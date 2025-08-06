#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI文件整理结果查看器 - 局域网服务器
支持局域网访问，提供文件预览和下载功能
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
try:
    import sys
    import os
    # 添加src目录到Python路径
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    from tidyfile.utils.app_paths import get_app_paths
    app_paths = get_app_paths()
    CACHE_DIR = app_paths.cache_dir
except ImportError:
    # 兼容旧版本
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

def convert_docx_to_pdf(docx_path, cache_key=None):
    """将Word文档转换为PDF（保持向后兼容）"""
    return convert_office_to_pdf_advanced(docx_path, cache_key)

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
    
    def send_error(self, code, message=None, explain=None):
        """重写send_error方法，支持UTF-8编码的错误消息"""
        try:
            print(f"[调试] 发送错误: {code}, 消息: {message}")
            # 设置响应状态码
            self.send_response(code, message)
            
            # 设置响应头
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 构建错误页面内容
            if message is None:
                message = self.responses[code][0]
            if explain is None:
                explain = self.responses[code][1]
            
            # 使用UTF-8编码构建错误页面
            error_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>错误 {code}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .error {{ color: #d32f2f; }}
        .code {{ font-weight: bold; }}
    </style>
</head>
<body>
    <h1 class="error">错误 {code}</h1>
    <p class="code">{message}</p>
    <p>{explain}</p>
</body>
</html>"""
            
            print(f"[调试] 准备发送错误页面，长度: {len(error_html)}")
            # 发送UTF-8编码的错误页面
            self.wfile.write(error_html.encode('utf-8'))
            print(f"[调试] 错误页面发送完成")
            
        except Exception as e:
            # 如果UTF-8编码失败，回退到默认的latin-1编码
            print(f"UTF-8错误编码失败，回退到默认编码: {e}")
            try:
                super().send_error(code, message, explain)
            except Exception as e2:
                print(f"默认send_error也失败: {e2}")
                # 最后的回退：发送简单的错误响应
                try:
                    self.send_response(code)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    error_msg = f"Error {code}: {message or 'Unknown error'}"
                    self.wfile.write(error_msg.encode('utf-8'))
                except Exception as e3:
                    print(f"所有错误处理方法都失败: {e3}")
    
    def get_client_info(self):
        """获取客户端信息"""
        client_ip = self.client_address[0]
        is_local_access = client_ip in ['127.0.0.1', 'localhost', '::1']
        is_local_network = client_ip.startswith(('192.168.', '10.', '172.'))
        
        print(f"客户端IP: {client_ip}, 本地访问: {is_local_access}, 局域网访问: {is_local_network}")
        
        return {
            'ip': client_ip,
            'is_local': is_local_access,
            'is_local_network': is_local_network,
            'is_remote': not (is_local_access or is_local_network)
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
        elif self.path == '/api/data-file-path':
            self.handle_data_file_path()
        elif self.path == '/api/data-file':
            self.handle_data_file()
        elif self.path.startswith('/api/check-file-exists'):
            self.handle_check_file_exists()
        elif self.path.startswith('/api/open-html-file'):
            self.handle_open_html_file()
        elif self.path == '/ai_organize_result.json':
            # 直接处理ai_organize_result.json文件请求
            self.handle_data_file()
        elif self.path == '/viewer.html':
            # 重定向到resources目录中的viewer.html
            self.path = '/resources/viewer.html'
            super().do_GET()
        elif self.path == '/favicon.ico':
            # 重定向到resources目录中的favicon.ico
            self.path = '/resources/favicon.ico'
            super().do_GET()
        elif self.path == '/weixin_article_renderer.html':
            # 重定向到resources目录中的weixin_article_renderer.html
            self.path = '/resources/weixin_article_renderer.html'
            super().do_GET()
        elif self.path.startswith('/') and self.path.endswith('.json'):
            # 处理JSON文件请求，这些文件可能在用户数据目录中
            self.handle_json_file_request()
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
        elif self.path == '/api/data-file-path':
            self.handle_data_file_path()
        elif self.path == '/api/data-file':
            self.handle_data_file()
        elif self.path == '/viewer.html':
            # 重定向到resources目录中的viewer.html
            self.path = '/resources/viewer.html'
            super().do_HEAD()
        elif self.path == '/favicon.ico':
            # 重定向到resources目录中的favicon.ico
            self.path = '/resources/favicon.ico'
            super().do_HEAD()
        elif self.path == '/weixin_article_renderer.html':
            # 重定向到resources目录中的weixin_article_renderer.html
            self.path = '/resources/weixin_article_renderer.html'
            super().do_HEAD()
        elif self.path.startswith('/') and self.path.endswith('.json'):
            # 处理JSON文件请求，这些文件可能在用户数据目录中
            self.handle_json_file_request()
        else:
            super().do_HEAD()
    
    def handle_clean_duplicates(self):
        """处理清理重复文件的请求
        只按文件名判断重复，保留每个文件的最新记录
        """
        try:
            json_file = app_paths.ai_results_file
            
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
            json_file = app_paths.ai_results_file
            
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
            json_file = app_paths.ai_results_file
            
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
            json_file = app_paths.ai_results_file
            
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
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': '服务器运行正常',
            'stats': resource_stats
        })
    
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
    
    def handle_data_file_path(self):
        """处理数据文件路径请求"""
        try:
            json_file = app_paths.ai_results_file
            file_exists = json_file.exists()
            
            self.send_json_response({
                'success': True,
                'file_path': str(json_file),
                'file_exists': file_exists,
                'file_name': json_file.name
            })
        except Exception as e:
            self.send_json_response({'success': False, 'message': f'获取文件路径失败: {str(e)}'})
    
    def handle_data_file(self):
        """处理数据文件内容请求"""
        try:
            json_file = app_paths.ai_results_file
            
            if not json_file.exists():
                self.send_error(404, "数据文件不存在")
                return
            
            # 读取文件内容
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = f.read()
            except Exception as e:
                self.send_error(500, f"读取文件失败: {str(e)}")
                return
            
            # 设置响应头
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 发送文件内容
            self.wfile.write(data.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"处理请求失败: {str(e)}")
    
    def handle_check_file_exists(self):
        """处理检查文件是否存在的请求"""
        try:
            # 解析查询参数
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            file_path = query_params.get('file', [None])[0]
            if not file_path:
                self.send_json_response({'exists': False, 'error': '缺少文件路径参数'})
                return
            
            # URL解码文件路径
            file_path = unquote(file_path)
            
            # 检查文件是否存在
            exists = os.path.exists(file_path)
            
            print(f"[调试] 检查文件存在性: {file_path} -> {exists}")
            
            self.send_json_response({'exists': exists, 'file_path': file_path})
            
        except Exception as e:
            print(f"[错误] 检查文件存在性失败: {e}")
            self.send_json_response({'exists': False, 'error': str(e)})
    
    def handle_open_html_file(self):
        """处理打开HTML文件的请求"""
        try:
            # 解析查询参数
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            file_path = query_params.get('file', [None])[0]
            if not file_path:
                self.send_error(400, "缺少文件路径参数")
                return
            
            # URL解码文件路径
            file_path = unquote(file_path)
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                self.send_error(404, f"HTML文件不存在: {file_path}")
                return
            
            # 检查文件是否在允许的目录中（安全考虑）
            allowed_dirs = [
                str(app_paths.user_data_dir),
                str(app_paths.results_dir),
                str(app_paths.weixin_articles_dir)
            ]
            
            file_path_normalized = os.path.normpath(file_path)
            is_allowed = any(file_path_normalized.startswith(os.path.normpath(allowed_dir)) 
                           for allowed_dir in allowed_dirs)
            
            if not is_allowed:
                self.send_error(403, f"访问被拒绝: {file_path}")
                return
            
            # 读取HTML文件内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except Exception as e:
                self.send_error(500, f"读取HTML文件失败: {str(e)}")
                return
            
            # 设置响应头
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 发送HTML内容
            self.wfile.write(html_content.encode('utf-8'))
            
            print(f"[信息] 成功提供HTML文件: {file_path}")
            
        except Exception as e:
            print(f"[错误] 处理HTML文件请求失败: {e}")
            self.send_error(500, f"处理HTML文件请求失败: {str(e)}")
    
    def handle_json_file_request(self):
        """处理JSON文件请求，支持从用户数据目录加载文件"""
        try:
            # 从URL路径中提取文件路径
            # 例如: /C:/Users/xiang/AppData/Roaming/TidyFile/data/results/weixin_articles/file.json
            # 需要解码并转换为实际文件路径
            file_path = self.path[1:]  # 移除开头的 '/'
            file_path = unquote(file_path)  # URL解码
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                self.send_error(404, f"文件不存在: {file_path}")
                return
            
            # 检查文件是否在允许的目录中（安全考虑）
            allowed_dirs = [
                str(app_paths.user_data_dir),
                str(app_paths.results_dir),
                str(app_paths.weixin_articles_dir)
            ]
            
            file_path_normalized = os.path.normpath(file_path)
            is_allowed = any(file_path_normalized.startswith(os.path.normpath(allowed_dir)) 
                           for allowed_dir in allowed_dirs)
            
            if not is_allowed:
                self.send_error(403, f"访问被拒绝: {file_path}")
                return
            
            # 读取文件内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = f.read()
            except Exception as e:
                self.send_error(500, f"读取文件失败: {str(e)}")
                return
            
            # 设置响应头
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 发送文件内容
            self.wfile.write(data.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"处理JSON文件请求失败: {str(e)}")
    
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
    
    def handle_local_open_file(self):
        """处理本地访问的文件打开请求 - 直接打开文件"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            file_path = data.get('filePath', '')
            print(f"本地访问 - 收到打开文件请求: {file_path}")
            
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
            print(f"本地访问 - 文件信息: 名称={file_name}, 扩展名={file_ext}")
            
            # 本地访问：直接使用系统默认程序打开文件
            print("本地访问 - 直接打开文件")
            success = self.open_file_on_server(file_path, file_ext, file_name)
            
            if success:
                print(f"本地访问 - 文件打开成功: {file_name}")
                self.send_json_response({
                    'success': True, 
                    'message': f'文件 "{file_name}" 已使用系统默认程序打开',
                    'action': 'opened'
                })
            else:
                print(f"本地访问 - 文件打开失败: {file_name}")
                self.send_json_response({
                    'success': False, 
                    'error': f'无法打开文件 "{file_name}"'
                })
                
        except Exception as e:
            print(f"本地访问 - 处理文件打开请求时出错: {str(e)}")
            self.send_json_response({'success': False, 'error': f'处理失败: {str(e)}'})
    
    def handle_remote_open_file(self):
        """处理远程访问的文件打开请求 - 返回下载链接"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            file_path = data.get('filePath', '')
            print(f"远程访问 - 收到打开文件请求: {file_path}")
            
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
            print(f"远程访问 - 文件信息: 名称={file_name}, 扩展名={file_ext}")
            
            # 远程访问：返回文件下载链接，让客户端下载后打开
            print("远程访问 - 返回文件下载链接")
            success = self.handle_remote_file_open(file_path, file_name, file_ext)
            
            if success:
                print(f"远程访问 - 文件处理成功: {file_name}")
            else:
                print(f"远程访问 - 文件处理失败: {file_name}")
                
        except Exception as e:
            print(f"远程访问 - 处理文件打开请求时出错: {str(e)}")
            self.send_json_response({'success': False, 'error': f'处理失败: {str(e)}'})
    
    def handle_open_file(self):
        """处理打开文件的请求（兼容旧版本）"""
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
            
            # 检测访问类型
            client_ip = self.client_address[0]
            is_local_access = client_ip in ['127.0.0.1', 'localhost', '::1']
            is_local_network = client_ip.startswith(('192.168.', '10.', '172.'))
            
            print(f"客户端IP: {client_ip}, 本地访问: {is_local_access}, 局域网访问: {is_local_network}")
            
            # 根据访问类型决定处理方式
            if is_local_access:
                # 本地访问：在服务器端打开文件
                print("本地访问，在服务器端打开文件")
                success = self.open_file_on_server(file_path, file_ext, file_name)
            else:
                # 局域网访问：返回文件下载链接，让客户端下载后打开
                print("局域网访问，返回文件下载链接")
                success = self.handle_remote_file_open(file_path, file_name, file_ext)
            
            if success:
                print(f"文件处理成功: {file_name}")
            else:
                print(f"文件处理失败: {file_name}")
                
        except Exception as e:
            print(f"处理请求异常: {e}")
            self.send_json_response({'success': False, 'error': f'处理请求失败: {str(e)}'})
    
    def open_file_on_server(self, file_path, file_ext, file_name):
        """在服务器端打开文件（本地访问）"""
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
            else:
                print(f"文件打开失败: {file_name}")
            
            return success
                
        except Exception as e:
            print(f"打开文件异常: {e}")
            return False
    
    def handle_remote_file_open(self, file_path, file_name, file_ext):
        """处理远程文件打开（局域网访问）"""
        try:
            # 获取服务器IP地址
            server_ip = get_local_ip()
            if not server_ip:
                server_ip = "localhost"
            
            # 构建文件下载URL
            encoded_path = quote(file_path)
            download_url = f"http://{server_ip}/api/download-file?path={encoded_path}"
            
            # 根据文件类型决定处理方式
            if self.should_preview_inline(file_ext):
                # 支持内联预览的文件，直接返回预览URL
                preview_url = f"http://{server_ip}/api/download-file?path={encoded_path}"
                self.send_json_response({
                    'success': True,
                    'message': f'文件 "{file_name}" 可以在浏览器中预览',
                    'type': 'preview',
                    'url': preview_url,
                    'fileName': file_name
                })
            else:
                # 不支持预览的文件，返回下载链接
                self.send_json_response({
                    'success': True,
                    'message': f'文件 "{file_name}" 已准备好下载',
                    'type': 'download',
                    'url': download_url,
                    'fileName': file_name
                })
            
            return True
            
        except Exception as e:
            print(f"处理远程文件打开异常: {e}")
            self.send_json_response({'success': False, 'error': f'处理远程文件失败: {str(e)}'})
            return False
    
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
    
    def handle_local_download_file(self):
        """处理本地访问的文件下载请求 - 直接下载文件"""
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
        """处理远程访问的文件下载请求 - 进行PDF转换和下载"""
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
            
            # 远程访问：进行Office文档转PDF
            original_file_path = file_path  # 保存原始文件路径
            if file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
                print(f"远程访问检测到Office文档，尝试转换为PDF: {file_path}")
                try:
                    pdf_path = convert_office_to_pdf_advanced(file_path)
                    if pdf_path and os.path.exists(pdf_path):
                        print(f"✅ Office文档转换成功，使用PDF文件: {pdf_path}")
                        file_path = pdf_path
                        file_name = os.path.basename(pdf_path)
                        file_ext = '.pdf'
                        file_size = os.path.getsize(pdf_path)
                    else:
                        print(f"❌ Office文档转换失败，使用原始文件: {original_file_path}")
                        # 转换失败时，确保使用原始文件
                        file_path = original_file_path
                        file_name = os.path.basename(original_file_path)
                        file_ext = os.path.splitext(file_name)[1].lower()
                        file_size = os.path.getsize(original_file_path)
                except Exception as conv_error:
                    print(f"❌ Office文档转换异常: {conv_error}")
                    print(f"使用原始文件: {original_file_path}")
                    # 转换异常时，确保使用原始文件
                    file_path = original_file_path
                    file_name = os.path.basename(original_file_path)
                    file_ext = os.path.splitext(file_name)[1].lower()
                    file_size = os.path.getsize(original_file_path)
            
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
    
    def handle_download_file(self):
        """处理文件下载请求（兼容旧版本）"""
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
            print(f"原始请求路径: {self.path}")
            print(f"解析后的文件路径: {file_path}")
            print(f"文件是否存在: {os.path.exists(file_path)}")
            print(f"文件路径类型: {type(file_path)}")
            print(f"文件路径长度: {len(file_path)}")
            
            # 尝试规范化路径
            try:
                normalized_path = os.path.normpath(file_path)
                print(f"规范化后的路径: {normalized_path}")
                print(f"规范化路径是否存在: {os.path.exists(normalized_path)}")
                if os.path.exists(normalized_path):
                    file_path = normalized_path
            except Exception as norm_error:
                print(f"路径规范化失败: {norm_error}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"文件不存在: {file_path}")
                # 直接返回404错误，不进行任何搜索
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                # HEAD请求不需要发送响应体
                if self.command != 'HEAD':
                    self.wfile.write(f"File not found: {file_path}".encode('utf-8'))
                return
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            

            
            # 检测访问类型
            client_ip = self.client_address[0]
            is_local_access = client_ip in ['127.0.0.1', 'localhost', '::1']
            is_local_network = client_ip.startswith(('192.168.', '10.', '172.'))
            
            print(f"客户端IP: {client_ip}, 本地访问: {is_local_access}, 局域网访问: {is_local_network}")
            
            # 只在局域网访问时进行Office文档转PDF
            original_file_path = file_path  # 保存原始文件路径
            if (is_local_network or not is_local_access) and file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
                print(f"局域网访问检测到Office文档，尝试转换为PDF: {file_path}")
                pdf_path = convert_office_to_pdf_advanced(file_path)
                if pdf_path and os.path.exists(pdf_path):
                    print(f"Office文档已转换为PDF，使用PDF文件: {pdf_path}")
                    file_path = pdf_path
                    file_name = os.path.basename(pdf_path)
                    file_ext = '.pdf'
                    file_size = os.path.getsize(pdf_path)
                else:
                    print(f"Office文档转换失败，使用原始文件: {original_file_path}")
                    # 转换失败时，确保使用原始文件
                    file_path = original_file_path
                    file_name = os.path.basename(original_file_path)
                    file_ext = os.path.splitext(file_name)[1].lower()
                    file_size = os.path.getsize(original_file_path)
            elif is_local_access and file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
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
        
        # 设置响应头 - 强制浏览器预览而不是下载
        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        # 关键：使用inline强制浏览器预览，不使用attachment
        self.send_header('Content-Disposition', f'inline; filename="{safe_filename}"; filename*=UTF-8\'\'{urllib.parse.quote(safe_filename)}')
        self.send_header('Content-Length', str(file_size))
        self.send_header('Access-Control-Allow-Origin', '*')
        # 添加缓存控制，提高加载速度
        self.send_header('Cache-Control', 'public, max-age=3600, immutable')  # 缓存1小时，不可变
        self.send_header('ETag', f'"{hashlib.md5(f"{file_path}_{file_size}".encode()).hexdigest()}"')
        # 添加X-Content-Type-Options防止MIME类型嗅探
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        
        # 分块读取和发送，提高大文件传输性能
        chunk_size = 1024 * 1024  # 1MB chunks
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()  # 立即发送数据
    
    def handle_pdf_preview(self, file_path, file_name, file_size):
        """专门处理PDF文件预览，优化性能"""
        try:
            # 检查是否支持Range请求（用于大文件分块传输）
            range_header = self.headers.get('Range')
            
            if range_header:
                # 处理Range请求，支持断点续传
                self.handle_pdf_range_request(file_path, file_name, file_size, range_header)
            else:
                # 完整文件请求 - 强制浏览器预览而不是下载
                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                # 关键：使用inline强制浏览器预览，不使用attachment
                self.send_header('Content-Disposition', f'inline; filename="{file_name}"; filename*=UTF-8\'\'{urllib.parse.quote(file_name)}')
                self.send_header('Content-Length', str(file_size))
                self.send_header('Accept-Ranges', 'bytes')  # 支持Range请求
                self.send_header('Access-Control-Allow-Origin', '*')
                # 添加更多缓存控制，提高加载速度
                self.send_header('Cache-Control', 'public, max-age=7200, immutable')  # 缓存2小时，不可变
                self.send_header('ETag', f'"{hashlib.md5(f"{file_path}_{file_size}".encode()).hexdigest()}"')
                # 添加X-Content-Type-Options防止MIME类型嗅探
                self.send_header('X-Content-Type-Options', 'nosniff')
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
        try:
            mime_type = self.get_mime_type(file_name)
            
            # 对文件名进行URL编码，避免编码错误
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
        # 将工作目录设置为项目根目录，这样服务器可以访问resources目录
        project_root = script_dir.parent
        os.chdir(project_root)
        
        # 检查必要文件是否存在
        # 首先尝试在resources目录中查找HTML文件
        resources_dir = script_dir.parent / 'resources'
        new_html_file = resources_dir / 'viewer.html'
        html_file = resources_dir / 'viewer.html'
        fallback_html_file = resources_dir / 'ai_result_viewer.html'
        
        # 如果resources目录中没有找到，则在scripts目录中查找
        if not new_html_file.exists():
            new_html_file = script_dir / 'viewer.html'
        if not html_file.exists():
            html_file = script_dir / 'viewer.html'
        if not fallback_html_file.exists():
            fallback_html_file = script_dir / 'ai_result_viewer.html'
        
        # JSON文件路径使用app_paths
        json_file = app_paths.ai_results_file
        
        # 创建HTTP服务器
        handler = CustomHTTPRequestHandler
        
        # 配置服务器参数，提高性能（简化配置，减少不必要的设置）
        socketserver.TCPServer.allow_reuse_address = True
        
        # 尝试启动服务器
        with socketserver.TCPServer((bind_address, port), handler) as httpd:
            # 设置连接超时
            httpd.timeout = CONNECTION_CONFIG['keepalive_timeout']
            
            # 启动连接管理器监控
            print("启动连接管理器...")
            connection_manager.start_monitoring()
            # 获取本机IP地址
            local_ip = get_local_ip()
            
            # 构建服务器URL
            if bind_address == "0.0.0.0":
                server_url = f"http://{local_ip}" if port == 80 else f"http://{local_ip}:{port}"
                localhost_url = f"http://localhost" if port == 80 else f"http://localhost:{port}"
            else:
                server_url = f"http://{bind_address}" if port == 80 else f"http://{bind_address}:{port}"
                localhost_url = server_url
            
            # 优先使用新的拆分组件viewer.html，如果不存在则使用viewer.html，最后使用ai_result_viewer.html
            if new_html_file.exists():
                primary_html = 'viewer.html'
                primary_url = f"{server_url}/viewer.html"
                localhost_primary_url = f"{localhost_url}/viewer.html"
                print(f"使用新的拆分组件: {new_html_file}")
            elif html_file.exists():
                primary_html = 'viewer.html'
                primary_url = f"{server_url}/viewer.html"
                localhost_primary_url = f"{localhost_url}/viewer.html"
                print(f"使用原始HTML文件: {html_file}")
            elif fallback_html_file.exists():
                primary_html = 'ai_result_viewer.html'
                primary_url = f"{server_url}/ai_result_viewer.html"
                localhost_primary_url = f"{localhost_url}/ai_result_viewer.html"
                print(f"注意: 使用备用HTML文件 {fallback_html_file}")
            else:
                print(f"错误: 找不到HTML文件 viewer.html、viewer.html 或 ai_result_viewer.html")
                return False
            
            if not json_file.exists():
                print(f"警告: JSON文件 {json_file} 不存在，将显示空数据")
            
            print(f"服务器已启动 - 本机: {localhost_primary_url}")
            print(f"连接配置: 最大连接数={CONNECTION_CONFIG['max_connections']}, 超时={CONNECTION_CONFIG['connection_timeout']}秒")
            
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
    port = 80  # 默认使用80端口，支持局域网访问
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
    
    # 智能端口选择：优先使用80端口，如果失败则尝试其他端口
    ports_to_try = [80, 8080, 8000, 8888]
    success = False
    
    for try_port in ports_to_try:
        print(f"尝试启动服务器在端口 {try_port}...")
        success = start_local_server(try_port, bind_address)
        if success:
            print(f"服务器成功启动在端口 {try_port}")
            break
        else:
            print(f"端口 {try_port} 启动失败，尝试下一个端口...")
    
    if not success:
        print("\n所有端口都无法启动服务器，请检查错误信息")
        print("可能的原因：")
        print("1. 防火墙阻止了端口访问")
        print("2. 需要管理员权限（对于80端口）")
        print("3. 网络配置问题")
        input("按回车键退出...")
        sys.exit(1)

if __name__ == "__main__":
    main()