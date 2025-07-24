import sys
import importlib
import subprocess

# (导入名, pip包名)
REQUIRED = [
    ("requests", "requests"),
    ("bs4", "beautifulsoup4"),
    ("html2text", "html2text"),
    ("fake_useragent", "fake-useragent"),
    ("markdown", "markdown"),
]

def install_missing_packages(missing_packages):
    """尝试自动安装缺失的包"""
    try:
        print(f"\n[自动安装] 尝试安装缺失的依赖包: {' '.join(missing_packages)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
        print("[自动安装] 依赖包安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[自动安装] 安装失败: {e}")
        return False

missing = []
for import_name, pip_name in REQUIRED:
    try:
        importlib.import_module(import_name)
    except ImportError:
        missing.append(pip_name)

if missing:
    print(f"\n[依赖缺失] 检测到缺失的依赖包: {' '.join(missing)}")
    
    # 尝试自动安装
    if install_missing_packages(missing):
        # 重新检查
        missing = []
        for import_name, pip_name in REQUIRED:
            try:
                importlib.import_module(import_name)
            except ImportError:
                missing.append(pip_name)
    
    if missing:
        print(f"\n[依赖缺失] 仍有依赖包缺失: {' '.join(missing)}")
        print("请手动安装以下依赖包：")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)
import os
import time
import random
import json
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import html2text
import argparse
import markdown  # 新增：用于Markdown转HTML
from ai_client_manager import chat_with_ai

# --- 配置 ---
ARTICLE_JSON = Path("weixin_manager/weixin_article.json")
AI_RESULT_JSON = Path("ai_organize_result.json")
ARTICLES_DIR = Path("weixin_manager/weixin_articles")
TIME_RANGE = (3, 6)
RETRY = 3

# --- 微信文章内容抓取 ---
ua = UserAgent()
def build_session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": ua.chrome,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://mp.weixin.qq.com/",
        "Cookie": (
            "uuid=123456; uid=123456; pac_uid=1_123456789; "
            "tvfe_boss_uuid=1_123456789; pgv_pvid=123456789"
        )
    })
    return sess

def safe_title(title: str) -> str:
    return "".join(c for c in title if c not in r'\\/:*?"<>|')[:80].strip()

def fetch_article(url: str, sess: requests.Session) -> dict | None:
    for attempt in range(1, RETRY + 1):
        try:
            resp = sess.get(url, timeout=15)
            if resp.status_code == 200:
                break
            print(f"[{attempt}/{RETRY}] 状态码 {resp.status_code}，重试…")
        except requests.RequestException as e:
            print(f"[{attempt}/{RETRY}] 网络错误 {e}，重试…")
        time.sleep(random.uniform(*TIME_RANGE))
    else:
        print("[错误] 获取失败，已跳过：", url)
        return None
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # 提取标题
    title_tag = soup.find("h1", id="activity-name")
    title = title_tag.get_text(strip=True) if title_tag else "无标题"
    
    # 提取作者
    author_tag = soup.find("a", id="js_name") or soup.find("span", class_="rich_media_meta_text")
    author = author_tag.get_text(strip=True) if author_tag else "未知作者"
    
    # 提取发表时间 - 尝试多种方式获取
    publish_time = ""
    import re
    
    # 方法1: 查找JavaScript变量中的时间（优先）
    script_tags = soup.find_all("script")
    for script in script_tags:
        if script.string and "createTime" in script.string:
            # 匹配 var createTime = '2025-07-15 12:06'; 格式
            match = re.search(r"var createTime = ['\"]([^'\"]+)['\"]", script.string)
            if match:
                publish_time = match.group(1)
                print(f"[调试] 从JavaScript获取到时间: {publish_time}")
                break
    
    # 方法2: 查找publish_time元素
    if not publish_time:
        time_tag = soup.find("em", id="publish_time")
        if time_tag:
            publish_time = time_tag.get_text(strip=True)
            print(f"[调试] 从publish_time元素获取到时间: {publish_time}")
    
    # 方法3: 查找rich_media_meta_text类的时间
    if not publish_time:
        time_tags = soup.find_all("span", class_="rich_media_meta_text")
        for tag in time_tags:
            text = tag.get_text(strip=True)
            # 检查是否包含时间格式
            if re.search(r'\d{4}-\d{2}-\d{2}|\d{2}-\d{2}|\d{2}:\d{2}', text):
                publish_time = text
                print(f"[调试] 从rich_media_meta_text获取到时间: {publish_time}")
                break
    
    if not publish_time:
        print("[警告] 未能获取到发表时间")
    
    # 提取正文内容
    content_div = soup.find("div", id="js_content")
    if not content_div:
        print("[警告] 找不到正文，已跳过：", url)
        return None
    
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.bypass_tables = False
    body_md = h.handle(str(content_div))
    
    return {
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "content": body_md,
        "url": url
    }

# --- AI摘要生成 ---
# 直接import file_reader.py中的FileReader
sys.path.insert(0, str(Path(__file__).parent))
from file_reader import FileReader



# --- 主流程 ---
def load_json(path):
    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_article_to_file(article_data: dict) -> str:
    """保存文章内容到本地文件"""
    # 确保目录存在
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成安全的文件名
    safe_filename = safe_title(article_data['title'])
    if not safe_filename:
        safe_filename = "无标题文章"
    
    # 生成文件名（添加时间戳避免重名）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{safe_filename}_{timestamp}.json"
    file_path = ARTICLES_DIR / filename
    
    # 保存文章数据
    article_json = {
        "title": article_data['title'],
        "author": article_data['author'],
        "publish_time": article_data['publish_time'],
        "content": article_data['content'],
        "url": article_data['url'],
        "saved_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    save_json(file_path, article_json)
    return str(file_path)

def save_article_to_html(article_data: dict) -> str:
    """
    保存文章内容为HTML文件（渲染Markdown为HTML）
    :param article_data: dict, 包含title, author, publish_time, content, url等
    :return: str, 保存的HTML文件路径
    """
    # 文件级注释：确保目录存在
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    # 变量级注释：生成安全的文件名
    safe_filename = safe_title(article_data['title'])
    if not safe_filename:
        safe_filename = "无标题文章"
    # 变量级注释：生成文件名（添加时间戳避免重名）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{safe_filename}_{timestamp}.html"
    file_path = ARTICLES_DIR / filename
    # 变量级注释：渲染Markdown为HTML
    try:
        html_content = markdown.markdown(article_data['content'], extensions=['extra', 'codehilite', 'tables'])
    except ImportError as e:
        html_content = f"<pre>Markdown模块未安装: {e}</pre>\n<pre>{article_data['content']}</pre>"
    except Exception as e:
        html_content = f"<pre>Markdown 渲染失败: {e}</pre>\n<pre>{article_data['content']}</pre>"
    # 变量级注释：读取HTML模板
    try:
        template_path = Path('weixin_article_template.html')
        template = template_path.read_text(encoding='utf-8')
    except Exception as e:
        raise RuntimeError(f"无法读取模板文件: {e}")
    # 变量级注释：填充模板变量
    html = template.replace('{{TITLE}}', article_data['title']) \
                  .replace('{{AUTHOR}}', article_data['author']) \
                  .replace('{{PUBLISH_TIME}}', article_data['publish_time']) \
                  .replace('{{SAVED_TIME}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S')) \
                  .replace('{{CONTENT}}', html_content) \
                  .replace('{{ORIGINAL_LINK}}', f'<a href="{article_data["url"]}" target="_blank">原文链接</a>' if article_data.get('url') else '')
    # 变量级注释：保存HTML文件
    try:
        file_path.write_text(html, encoding='utf-8')
    except Exception as e:
        raise RuntimeError(f"无法保存HTML文件: {e}")
    return str(file_path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary_length', type=int, default=200, help='AI摘要长度')
    args = parser.parse_args()
    summary_length = args.summary_length
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 启动微信文章AI摘要生成脚本，摘要长度：{summary_length}")
    if not ARTICLE_JSON.exists():
        print(f"未找到 {ARTICLE_JSON}，请先备份收藏文章！")
        return
    articles = load_json(ARTICLE_JSON)
    if not articles:
        print("没有可处理的微信文章记录！")
        return
    ai_results = load_json(AI_RESULT_JSON)
    # 创建已存在文章的集合（基于标题和链接）
    exist_articles = set()
    for item in ai_results:
        title = item.get('文章标题', '').strip()
        url = item.get('源文件路径', '').strip()
        if title and url:
            exist_articles.add((title, url))
    sess = build_session()
    new_records = []
    
    for idx, art in enumerate(articles, 1):
        title = art.get('title', '').strip()
        url = art.get('url', '').strip()
        if not title or not url:
            continue
        # 检查文章是否已存在（基于标题和链接）
        if (title, url) in exist_articles:
            print(f"[{idx}/{len(articles)}] 已存在，跳过：{title}")
            continue
        print(f"[{idx}/{len(articles)}] 处理：{title}")
        
        # 获取文章内容
        article_data = fetch_article(url, sess)
        if not article_data:
            print(f"[警告] 获取失败，跳过：{title}")
            continue
        
        # 保存文章内容到本地文件
        try:
            local_file_path = save_article_to_file(article_data)
            html_file_path = save_article_to_html(article_data)  # 新增：保存为HTML
            print(f"[保存] 文章内容已保存到：{local_file_path}，HTML：{html_file_path}")
        except Exception as e:
            print(f"[错误] 保存文章失败：{e}")
            continue
        
        # AI生成摘要
        try:
            # 构建摘要提示词
            prompt = f"""请为以下微信文章生成一个{summary_length}字以内的中文摘要。

文章标题：{article_data['title']}
文章作者：{article_data['author']}
文章内容：
{article_data['content'][:3000]}

要求：
1. 概括文章的主要内容和主题
2. 突出关键信息和要点
3. 语言简洁明了
4. 字数控制在{summary_length}字以内
5. 直接输出摘要内容，不要包含任何思考过程或说明文字
6. 不要使用"<think>"标签或任何思考过程描述

摘要：/no_think"""

            # 在传递给大模型的完整内容最尾部添加/no_think标签
            final_prompt = prompt

            # 使用系统提示词来抑制思考过程
            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的文章摘要助手。重要：不要输出任何推理过程、思考步骤或解释。直接按要求输出结果。只输出摘要内容，不要包含任何其他信息。'
                },
                {
                    'role': 'user',
                    'content': final_prompt
                }
            ]
            
            summary_text = chat_with_ai(messages)
            
            # 清理可能的思考过程标签和内容
            summary_text = summary_text.replace('<think>', '').replace('</think>', '').strip()
            
            # 移除常见的思考过程开头
            think_prefixes = [
                '好的，', '好，', '嗯，', '我来', '我需要', '首先，', '让我', '现在我要',
                '用户希望', '用户要求', '用户让我', '根据', '基于', '考虑到', '让我先仔细看看',
                '用户给了我这个查询', '用户给了我这个任务', '用户给了一个任务',
                '首先，我得看一下', '首先，我要理解', '首先，我得仔细看看',
                '好的，用户让我', '用户让我生成', '内容来自文件', '重点包括', '首先，我需要确认'
            ]
            
            # 更激进的清理：移除所有以思考过程开头的句子
            lines = summary_text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 检查是否以思考过程开头
                is_think_line = False
                for prefix in think_prefixes:
                    if line.lower().startswith(prefix.lower()):
                        is_think_line = True
                        break
                
                # 如果不是思考过程，保留这一行
                if not is_think_line:
                    cleaned_lines.append(line)
            
            # 如果清理后没有内容，尝试更简单的方法
            if not cleaned_lines:
                # 找到第一个不是思考过程的句子
                sentences = summary_text.split('。')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    # 检查是否以思考过程开头
                    is_think_sentence = False
                    for prefix in think_prefixes:
                        if sentence.lower().startswith(prefix.lower()):
                            is_think_sentence = True
                            break
                    
                    if not is_think_sentence:
                        cleaned_lines.append(sentence)
                        break
            
            # 如果还是没有内容，使用原始摘要的最后一部分
            if not cleaned_lines:
                # 取最后100个字符作为摘要
                summary_text = summary_text[-100:] if len(summary_text) > 100 else summary_text
            
            # 重新组合清理后的内容
            if cleaned_lines:
                summary_text = '。'.join(cleaned_lines)
            
            # 确保摘要长度不超过限制
            if len(summary_text) > summary_length:
                summary_text = summary_text[:summary_length-3] + "..."
            
        except Exception as e:
            print(f"[错误] AI摘要失败：{e}")
            continue
        
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record = {
            "处理时间": now_str,
            "文章标题": article_data['title'],
            "文章作者": article_data['author'],
            "发表时间": article_data['publish_time'],
            "文章摘要": summary_text,
            "源文件路径": url,
            "最匹配的目标目录": url,
            "最终目标路径": local_file_path
        }
        ai_results.append(record)
        new_records.append(record)
        print(f"[成功] 已生成摘要并追加：{title}")
        save_json(AI_RESULT_JSON, ai_results)
        time.sleep(random.uniform(*TIME_RANGE))
    
    print(f"全部处理完成，新增 {len(new_records)} 条摘要。")

if __name__ == "__main__":
    main() 