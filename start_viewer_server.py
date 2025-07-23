#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地HTTP服务器启动脚本
用于解决浏览器CORS策略限制，使ai_result_viewer.html能够正常加载JSON文件

作者: AI助手
创建时间: 2025-01-20
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
from pathlib import Path
from datetime import datetime

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    自定义HTTP请求处理器，支持清理重复文件的API和心跳检测
    """
    
    # 类变量，用于跟踪最后一次心跳时间
    last_heartbeat = time.time()
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == '/api/clean-duplicates':
            self.handle_clean_duplicates()
        elif self.path == '/api/open-file':
            self.handle_open_file()
        elif self.path == '/api/heartbeat':
            self.handle_heartbeat()
        else:
            self.send_error(404, "API endpoint not found")
    
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
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
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
    
    def handle_open_file(self):
        """处理打开文件的请求"""
        try:
            # 读取请求体
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            file_path = request_data.get('filePath')
            if not file_path:
                self.send_json_response({'success': False, 'error': '文件路径不能为空'})
                return
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                self.send_json_response({'success': False, 'error': f'文件不存在: {file_path}'})
                return
            
            # 使用os.startfile直接打开文件（等同于双击文件）
            try:
                # os.startfile是Windows专用的方法，会使用默认程序打开文件
                os.startfile(file_path)
                
                self.send_json_response({
                    'success': True, 
                    'message': f'文件已打开: {file_path}'
                })
                    
            except OSError as e:
                # 处理文件不存在、权限不足等系统错误
                self.send_json_response({
                    'success': False, 
                    'error': f'无法打开文件: {str(e)}'
                })
            except Exception as e:
                # 处理其他未知错误
                self.send_json_response({
                    'success': False, 
                    'error': f'打开文件失败: {str(e)}'
                })
                
        except json.JSONDecodeError:
            self.send_json_response({'success': False, 'error': '请求数据格式错误'})
        except Exception as e:
            self.send_json_response({'success': False, 'error': f'处理请求失败: {str(e)}'})
    
    def remove_duplicate_files(self, data):
        """移除重复文件，只保留每个文件的最新记录
        - 所有文件：只按文件名判断重复，保留最新的记录
        """
        file_map = {}
        # 按处理时间排序，最新的在前
        data.sort(key=lambda x: datetime.fromisoformat(x.get('处理时间', '1970-01-01 00:00:00')), reverse=True)
        for item in data:
            file_name = item.get('文件名')
            # 兼容文章标题字段
            if not file_name:
                file_name = item.get('文章标题', '')
            
            if file_name and file_name not in file_map:
                file_map[file_name] = item
        return list(file_map.values())
    
    def send_json_response(self, data):
        """发送JSON响应"""
        response = json.dumps(data, ensure_ascii=False)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def handle_heartbeat(self):
        """处理心跳请求"""
        CustomHTTPRequestHandler.last_heartbeat = time.time()
        self.send_json_response({'status': 'alive', 'timestamp': time.time()})
    
    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def monitor_browser_connection(httpd):
    """
    监控浏览器连接状态，如果超过60秒没有心跳，则关闭服务器
    
    Args:
        httpd: HTTP服务器实例
    """
    # 等待60秒后开始监控，给浏览器足够时间启动和发送第一次心跳
    time.sleep(60)
    
    while True:
        time.sleep(15)  # 每15秒检查一次
        current_time = time.time()
        time_since_last_heartbeat = current_time - CustomHTTPRequestHandler.last_heartbeat
        
        # 如果超过45秒没有心跳，认为浏览器已关闭
        if time_since_last_heartbeat > 45:
            print("\n检测到浏览器已关闭，正在停止服务器...")
            httpd.shutdown()
            break

def start_local_server(port=8000):
    """
    启动本地HTTP服务器
    
    Args:
        port (int): 服务器端口号，默认8000
    """
    try:
        # 确保在正确的目录下启动服务器
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        
        # 检查必要文件是否存在
        html_file = script_dir / 'ai_result_viewer.html'
        json_file = script_dir / 'ai_organize_result.json'
        
        if not html_file.exists():
            print(f"错误: 找不到HTML文件 {html_file}")
            return False
            
        if not json_file.exists():
            print(f"警告: JSON文件 {json_file} 不存在，将显示空数据")
            # 创建空的JSON文件
            with open(json_file, 'w', encoding='utf-8') as f:
                f.write('[]')
        
        # 创建HTTP服务器
        handler = CustomHTTPRequestHandler
        
        # 尝试启动服务器
        with socketserver.TCPServer(("", port), handler) as httpd:
            server_url = f"http://localhost:{port}"
            viewer_url = f"{server_url}/ai_result_viewer.html"
            
            print(f"\n=== AI结果查看器服务器 ===")
            print(f"服务器地址: {server_url}")
            print(f"查看器地址: {viewer_url}")
            print(f"API端点:")
            print(f"  - 清理重复文件: {server_url}/api/clean-duplicates")
            print(f"  - 打开文件: {server_url}/api/open-file")
            print(f"  - 心跳检测: {server_url}/api/heartbeat")
            print(f"工作目录: {script_dir}")
            print(f"按 Ctrl+C 停止服务器，或关闭浏览器自动停止")
            print("=" * 40)
            
            # 自动打开浏览器
            try:
                webbrowser.open(viewer_url)
                print(f"已在浏览器中打开: {viewer_url}")
            except Exception as e:
                print(f"无法自动打开浏览器: {e}")
                print(f"请手动访问: {viewer_url}")
            
            print("\n服务器正在运行...")
            
            # 启动浏览器连接监控线程
            monitor_thread = threading.Thread(target=monitor_browser_connection, args=(httpd,), daemon=True)
            monitor_thread.start()
            
            # 启动服务器
            httpd.serve_forever()
            
    except OSError as e:
        if e.errno == 10048:  # 端口被占用
            print(f"错误: 端口 {port} 已被占用，尝试使用端口 {port + 1}")
            return start_local_server(port + 1)
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
    print("AI结果查看器 - 本地服务器启动器")
    print("解决浏览器CORS策略限制问题")
    
    # 检查命令行参数
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"无效的端口号: {sys.argv[1]}，使用默认端口 8000")
    
    # 启动服务器
    success = start_local_server(port)
    
    if not success:
        print("\n服务器启动失败，请检查错误信息")
        input("按回车键退出...")
        sys.exit(1)

if __name__ == "__main__":
    main()