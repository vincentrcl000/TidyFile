import sys
import importlib
import subprocess

# (导入名, pip包名)
REQUIRED = [
    ("requests", "requests"),
    ("bs4", "beautifulsoup4"),
    ("html2text", "html2text"),
    ("fake_useragent", "fake-useragent"),
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
    reader = FileReader(model_name=None, host="http://localhost:11434")  # 自动选择模型，优先qwen3系列
    reader.initialize_ollama()  # 强制初始化ollama客户端
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
            summary = reader.generate_summary(article_data['content'], max_summary_length=summary_length)
            if isinstance(summary, dict):
                summary_text = summary.get('summary', '') or summary.get('文件摘要', '')
            else:
                summary_text = str(summary)
            
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

# --- FileReader补充方法 ---
# 为FileReader动态添加 generate_summary_from_text 方法
if not hasattr(FileReader, 'generate_summary_from_text'):
    def generate_summary_from_text(self, text, max_summary_length=200):
        prompt = self._build_summary_prompt(text, max_summary_length)
        return self._chat_with_retry([
            {"role": "user", "content": prompt}
        ])
    FileReader.generate_summary_from_text = generate_summary_from_text

if __name__ == "__main__":
    main() 