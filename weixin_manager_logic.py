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
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"接口请求失败: {e}")
    
    def parse_wechat_links(self, raw_text):
        """
        解析原始文本，提取所有[链接|标识的消息
        :param raw_text: 接口返回的文本
        :return: 文章列表 [{"time": "07-20 23:18:23", "title": "标题", "url": "链接"}]
        """
        articles = []
        
        # 匹配格式：我 07-20 23:18:36\n[链接|标题](链接)
        pattern = re.compile(
            r"^我 (\d{2}-\d{2} \d{2}:\d{2}:\d{2})\n\[链接\|(.*?)\]\((https?://[^\)]+)\)", 
            re.MULTILINE | re.DOTALL
        )
        
        matches = pattern.finditer(raw_text)
        for match in matches:
            time_str = match.group(1).strip()
            title = match.group(2).strip()
            url = match.group(3).strip()
            
            articles.append({
                "time": time_str,
                "title": title,
                "url": url
            })
        
        return articles
    
    def save_wechat_articles(self, articles):
        """
        保存文章到JSON文件
        :param articles: 文章列表
        :return: 保存的文件路径
        """
        # 创建保存目录
        os.makedirs(self.save_dir, exist_ok=True)
        save_path = os.path.join(self.save_dir, self.save_file)
        
        # 读取现有数据（如果存在）
        existing_articles = []
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_articles = existing_data
            except (json.JSONDecodeError, IOError):
                pass
        
        # 合并新数据
        all_articles = existing_articles + articles
        
        # 去重（基于URL）
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article.get('url') not in seen_urls:
                seen_urls.add(article.get('url'))
                unique_articles.append(article)
        
        # 保存到文件
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(unique_articles, f, ensure_ascii=False, indent=2)
            return save_path
        except IOError as e:
            raise Exception(f"保存文件失败: {e}")
    
    def backup_wechat_favorites(self, talker, start_date, end_date):
        """
        完整的微信收藏文章备份流程
        :param talker: 收藏账号
        :param start_date: 起始日期
        :param end_date: 结束日期
        :return: (成功数量, 保存路径)
        """
        # 1. 拉取数据
        raw_text = self.fetch_wechat_favorites(talker, start_date, end_date)
        
        # 2. 解析文章
        articles = self.parse_wechat_links(raw_text)
        
        # 3. 保存到文件
        save_path = self.save_wechat_articles(articles)
        
        return len(articles), save_path
    
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