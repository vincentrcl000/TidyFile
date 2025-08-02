import os
import re
import json
import requests
from datetime import datetime
from pathlib import Path

class WeixinManagerLogic:
    """微信信息管理后端逻辑"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:5030"
        self.save_dir = "weixin_manager"
        self.save_file = "weixin_article.json"
    
    def fetch_wechat_favorites(self, talker, start_date, end_date):
        """
        拉取微信收藏文章接口
        :param talker: 收藏账号
        :param start_date: 起始日期 YYYY-MM-DD
        :param end_date: 结束日期 YYYY-MM-DD
        :return: 原始文本内容
        """
        try:
            url = f"{self.base_url}/api/v1/chatlog"
            params = {
                "time": f"{start_date}~{end_date}",
                "talker": talker
            }
            print(f"[微信接口] 正在连接API服务器: {self.base_url}")
            print(f"[微信接口] 正在请求接口: {url}")
            print(f"[微信接口] 请求参数: 账号={talker}, 时间范围={start_date}~{end_date}")
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            print(f"[微信接口] API连接成功！")
            print(f"[微信接口] 服务器响应状态码: {response.status_code}")
            print(f"[微信接口] 响应数据长度: {len(response.text)} 字符")
            
            # 检查响应内容是否包含有效数据
            if len(response.text.strip()) == 0:
                print(f"[微信接口] 警告: 服务器返回空数据")
            elif "error" in response.text.lower():
                print(f"[微信接口] 警告: 服务器返回错误信息")
            else:
                print(f"[微信接口] 数据获取成功，开始解析...")
            
            return response.text
        except requests.exceptions.ConnectionError as e:
            print(f"[微信接口] 连接失败: 无法连接到API服务器 {self.base_url}")
            print(f"[微信接口] 请检查API服务是否已启动")
            raise Exception(f"API连接失败: {e}")
        except requests.exceptions.Timeout as e:
            print(f"[微信接口] 请求超时: 服务器响应时间过长")
            raise Exception(f"API请求超时: {e}")
        except requests.exceptions.RequestException as e:
            print(f"[微信接口] 请求失败: {e}")
            raise Exception(f"接口请求失败: {e}")
    
    def parse_wechat_links(self, raw_text):
        """
        解析原始文本，提取所有[链接|标识的消息
        :param raw_text: 接口返回的文本
        :return: 文章列表 [{"time": "07-20 23:18:23", "title": "标题", "url": "链接"}]
        """
        articles = []
        
        print(f"[解析] 开始解析微信收藏文章数据...")
        print(f"[解析] 原始数据长度: {len(raw_text)} 字符")
        
        # 检查原始数据是否为空
        if not raw_text.strip():
            print(f"[解析] 警告: 原始数据为空，无法解析")
            return articles
        
        # 匹配格式：[链接|标题](链接)
        pattern = re.compile(
            r"\[链接\|(.*?)\]\((https?://[^\)]+)\)", 
            re.MULTILINE | re.DOTALL
        )
        
        print(f"[解析] 正在使用正则表达式匹配文章链接...")
        matches = pattern.finditer(raw_text)
        
        match_count = 0
        for match in matches:
            match_count += 1
            title = match.group(1).strip()
            url = match.group(2).strip()
            
            # 尝试从上下文获取时间信息
            match_start = match.start()
            context_before = raw_text[max(0, match_start-200):match_start]
            
            # 查找时间戳模式
            time_pattern = re.compile(r"(\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
            time_matches = list(time_pattern.finditer(context_before))
            
            if time_matches:
                time_str = time_matches[-1].group(1)  # 取最近的时间戳
            else:
                time_str = "未知时间"
            
            print(f"[解析] 找到第 {match_count} 篇文章: {title[:30]}... (时间: {time_str})")
            
            articles.append({
                "处理时间": time_str,
                "文章标题": title,
                "源文件路径": url
            })
        
        print(f"[解析] 解析完成！")
        print(f"[解析] 成功识别到 {len(articles)} 篇收藏文章")
        
        if len(articles) == 0:
            print(f"[解析] 提示: 未找到任何收藏文章，请检查:")
            print(f"[解析] 1. 收藏账号是否正确")
            print(f"[解析] 2. 时间范围是否包含收藏记录")
            print(f"[解析] 3. 是否确实有收藏文章")
        
        return articles
    
    def save_wechat_articles(self, articles):
        """
        保存文章到JSON文件
        :param articles: 文章列表
        :return: 保存的文件路径
        """
        print(f"[保存] 开始保存文章数据...")
        print(f"[保存] 本次新增文章: {len(articles)} 篇")
        
        # 创建保存目录
        print(f"[保存] 正在创建保存目录: {self.save_dir}")
        os.makedirs(self.save_dir, exist_ok=True)
        save_path = os.path.join(self.save_dir, self.save_file)
        print(f"[保存] 文件保存路径: {save_path}")
        
        # 读取现有数据（如果存在）
        existing_articles = []
        if os.path.exists(save_path):
            try:
                print(f"[保存] 检测到现有文件，正在读取...")
                with open(save_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_articles = existing_data
                print(f"[保存] 成功读取现有文章: {len(existing_articles)} 篇")
            except (json.JSONDecodeError, IOError) as e:
                print(f"[保存] 读取现有文件失败: {e}")
                print(f"[保存] 将创建新的文件")
        else:
            print(f"[保存] 未找到现有文件，将创建新文件")
        
        # 合并新数据
        all_articles = existing_articles + articles
        print(f"[保存] 合并数据完成，总文章数: {len(all_articles)} 篇")
        
        # 去重（基于URL）
        print(f"[保存] 正在执行去重操作...")
        seen_urls = set()
        unique_articles = []
        duplicate_count = 0
        
        for article in all_articles:
            if article.get('源文件路径') not in seen_urls:
                seen_urls.add(article.get('源文件路径'))
                unique_articles.append(article)
            else:
                duplicate_count += 1
        
        print(f"[保存] 去重完成！")
        print(f"[保存] 去重前: {len(all_articles)} 篇")
        print(f"[保存] 去重后: {len(unique_articles)} 篇")
        print(f"[保存] 移除重复: {duplicate_count} 篇")
        
        # 保存到文件
        try:
            print(f"[保存] 正在写入文件...")
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(unique_articles, f, ensure_ascii=False, indent=2)
            print(f"[保存] 文件写入成功！")
            print(f"[保存] 最终保存路径: {save_path}")
            print(f"[保存] 文件大小: {os.path.getsize(save_path)} 字节")
            return save_path
        except IOError as e:
            print(f"[保存] 文件写入失败: {e}")
            raise Exception(f"保存文件失败: {e}")
    
    def backup_wechat_favorites(self, talker, start_date, end_date):
        """
        完整的微信收藏文章备份流程
        :param talker: 收藏账号
        :param start_date: 起始日期
        :param end_date: 结束日期
        :return: (成功数量, 保存路径)
        """
        print(f"[备份] ===== 微信收藏文章备份任务开始 =====")
        print(f"[备份] 收藏账号: {talker}")
        print(f"[备份] 时间范围: {start_date} ~ {end_date}")
        print(f"[备份] API服务器: {self.base_url}")
        print(f"[备份] 保存目录: {self.save_dir}")
        
        try:
            # 1. 拉取数据
            print(f"[备份] 步骤1: 正在连接API并拉取数据...")
            raw_text = self.fetch_wechat_favorites(talker, start_date, end_date)
            
            # 2. 解析文章
            print(f"[备份] 步骤2: 正在解析收藏文章...")
            articles = self.parse_wechat_links(raw_text)
            
            # 3. 保存到文件
            print(f"[备份] 步骤3: 正在保存文章数据...")
            save_path = self.save_wechat_articles(articles)
            
            print(f"[备份] ===== 备份任务完成 =====")
            print(f"[备份] 本次成功处理: {len(articles)} 篇文章")
            print(f"[备份] 数据已保存到: {save_path}")
            
            # 返回实际新增的文章数量（解析出的文章数量）
            return len(articles), save_path
            
        except Exception as e:
            print(f"[备份] ===== 备份任务失败 =====")
            print(f"[备份] 错误信息: {e}")
            raise e
    
    def get_saved_articles(self):
        """
        获取已保存的文章列表
        :return: 文章列表
        """
        save_path = os.path.join(self.save_dir, self.save_file)
        if not os.path.exists(save_path):
            return []
        
        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                articles = json.load(f)
                return articles if isinstance(articles, list) else []
        except (json.JSONDecodeError, IOError):
            return [] 