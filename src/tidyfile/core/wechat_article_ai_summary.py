import sys
import importlib
import subprocess
import shutil
import tempfile
import threading
# fcntl 是 Unix/Linux 系统特有的，在 Windows 上不可用
try:
    import fcntl
except ImportError:
    fcntl = None
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
from tidyfile.ai.client_manager import chat_with_ai

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

# --- 配置 ---
ARTICLE_JSON = Path("weixin_manager/weixin_article.json")
AI_RESULT_JSON = Path("ai_organize_result.json")
ARTICLES_DIR = Path("weixin_manager/weixin_articles")
TIME_RANGE = (3, 6)
RETRY = 3

# 文件锁管理器
class FileLockManager:
    def __init__(self):
        self._locks = {}
        self._lock = threading.Lock()
    
    def acquire_lock(self, file_path):
        """获取文件锁"""
        with self._lock:
            if file_path not in self._locks:
                self._locks[file_path] = threading.Lock()
            return self._locks[file_path]
    
    def release_lock(self, file_path):
        """释放文件锁"""
        with self._lock:
            if file_path in self._locks:
                del self._locks[file_path]

# 全局文件锁管理器
file_lock_manager = FileLockManager()

def validate_json_data(data):
    """验证JSON数据的有效性"""
    if not isinstance(data, list):
        print(f"[警告] JSON数据不是列表格式，实际类型: {type(data)}")
        return False
    
    # 检查每个记录的基本结构
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            print(f"[警告] 第{i}条记录不是字典格式")
            return False
    
    return True

def validate_wechat_article_record(record):
    """验证微信文章记录的有效性（只验证新记录）"""
    if not isinstance(record, dict):
        print(f"[警告] 记录不是字典格式")
        return False
    
    # 检查必要字段
    required_fields = ['处理时间', '文章标题', '源文件路径']
    for field in required_fields:
        if field not in record:
            print(f"[警告] 记录缺少必要字段: {field}")
            return False
    
    return True

def is_file_being_written(file_path, check_interval=1.0, max_checks=3):
    """检测文件是否正在被写入"""
    if not file_path.exists():
        return False
    
    try:
        # 获取初始文件大小和修改时间
        initial_size = file_path.stat().st_size
        initial_mtime = file_path.stat().st_mtime
        
        # 等待一段时间后再次检查
        time.sleep(check_interval)
        
        # 再次获取文件大小和修改时间
        current_size = file_path.stat().st_size
        current_mtime = file_path.stat().st_mtime
        
        # 如果文件大小或修改时间发生变化，说明文件正在被写入
        if current_size != initial_size or current_mtime != initial_mtime:
            return True
        
        # 多次检查以确保准确性
        for _ in range(max_checks - 1):
            time.sleep(check_interval)
            current_size = file_path.stat().st_size
            current_mtime = file_path.stat().st_mtime
            if current_size != initial_size or current_mtime != initial_mtime:
                return True
        
        return False
        
    except Exception as e:
        print(f"[警告] 检测文件写入状态失败: {e}")
        return False

def wait_for_file_stable(file_path, max_wait_time=30, check_interval=1.0):
    """等待文件写入完成"""
    if not file_path.exists():
        return True
    
    print(f"[等待] 等待文件写入完成: {file_path}")
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        if not is_file_being_written(file_path, check_interval=check_interval, max_checks=2):
            print(f"[等待] 文件写入完成: {file_path}")
            return True
        print(f"[等待] 文件仍在写入中，继续等待... ({time.time() - start_time:.1f}s)")
    
    print(f"[超时] 等待文件写入完成超时: {file_path}")
    return False

def create_backup(file_path):
    """创建文件备份"""
    if not file_path.exists():
        return None
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = file_path.with_suffix(f'.backup_{timestamp}.json')
        shutil.copy2(file_path, backup_path)
        print(f"[备份] 已创建备份文件: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"[警告] 创建备份失败: {e}")
        return None

def atomic_write_json(file_path, data):
    """原子性写入JSON文件"""
    # 验证数据
    if not validate_json_data(data):
        raise ValueError("JSON数据格式无效")
    
    # 创建临时文件
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            encoding='utf-8', 
            suffix='.json', 
            delete=False,
            dir=file_path.parent
        )
        
        # 写入临时文件
        json.dump(data, temp_file, ensure_ascii=False, indent=2)
        temp_file.flush()
        os.fsync(temp_file.fileno())  # 强制写入磁盘
        temp_file.close()
        
        # 原子性移动文件
        temp_path = Path(temp_file.name)
        shutil.move(str(temp_path), str(file_path))
        
        print(f"[保存] 原子性写入成功: {file_path}")
        return True
        
    except Exception as e:
        print(f"[错误] 原子性写入失败: {e}")
        # 清理临时文件
        if temp_file and temp_file.name:
            try:
                os.unlink(temp_file.name)
            except:
                pass
        raise

def load_json(path):
    """安全加载JSON文件"""
    if not path.exists():
        print(f"[信息] 文件不存在，将创建新文件: {path}")
        return []
    
    # 检查文件是否正在被写入
    if is_file_being_written(path):
        print(f"[警告] 检测到文件正在被写入: {path}")
        print(f"[建议] 请等待写入完成后再运行程序")
        raise RuntimeError(f"文件正在被写入，无法安全加载: {path}")
    
    # 获取文件锁
    lock = file_lock_manager.acquire_lock(str(path))
    with lock:
        try:
            # 创建备份
            backup_path = create_backup(path)
            
            # 检查文件大小，如果文件太小可能是写入中断
            file_size = path.stat().st_size
            if file_size < 10:  # 小于10字节可能是写入中断
                print(f"[警告] 文件大小异常小({file_size}字节)，可能是写入中断: {path}")
                if backup_path and backup_path.exists():
                    print(f"[恢复] 尝试从备份恢复: {backup_path}")
                    try:
                        with open(backup_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if validate_json_data(data):
                            print(f"[恢复] 从备份恢复成功")
                            return data
                    except Exception as e:
                        print(f"[错误] 从备份恢复失败: {e}")
                # 如果无法恢复，抛出异常而不是返回空列表
                raise RuntimeError(f"文件可能正在写入中，无法安全加载: {path}")
            
            # 读取文件
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 检查文件内容是否完整（简单的JSON完整性检查）
            content = content.strip()
            if not content:
                print(f"[警告] 文件为空: {path}")
                if backup_path and backup_path.exists():
                    print(f"[恢复] 尝试从备份恢复: {backup_path}")
                    try:
                        with open(backup_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if validate_json_data(data):
                            print(f"[恢复] 从备份恢复成功")
                            return data
                    except Exception as e:
                        print(f"[错误] 从备份恢复失败: {e}")
                raise RuntimeError(f"文件为空，可能正在写入中: {path}")
            
            # 检查JSON是否完整（简单的括号匹配）
            if not (content.startswith('[') and content.endswith(']')):
                print(f"[警告] JSON格式不完整，可能是写入中断: {path}")
                if backup_path and backup_path.exists():
                    print(f"[恢复] 尝试从备份恢复: {backup_path}")
                    try:
                        with open(backup_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if validate_json_data(data):
                            print(f"[恢复] 从备份恢复成功")
                            return data
                    except Exception as e:
                        print(f"[错误] 从备份恢复失败: {e}")
                raise RuntimeError(f"JSON格式不完整，可能正在写入中: {path}")
            
            # 尝试解析JSON
            data = json.loads(content)
            
            # 验证数据
            if not validate_json_data(data):
                print(f"[警告] 文件数据格式无效: {path}")
                if backup_path and backup_path.exists():
                    print(f"[恢复] 尝试从备份恢复: {backup_path}")
                    try:
                        with open(backup_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if validate_json_data(data):
                            print(f"[恢复] 从备份恢复成功")
                            return data
                    except Exception as e:
                        print(f"[错误] 从备份恢复失败: {e}")
                # 如果数据格式无效但文件存在，抛出异常而不是返回空列表
                raise RuntimeError(f"文件数据格式无效，可能正在写入中: {path}")
            
            print(f"[加载] 成功加载 {len(data)} 条记录: {path}")
            return data
            
        except json.JSONDecodeError as e:
            print(f"[错误] JSON解析失败: {e}")
            # 尝试从备份恢复
            if backup_path and backup_path.exists():
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if validate_json_data(data):
                        print(f"[恢复] 从备份恢复成功")
                        return data
                except Exception as restore_e:
                    print(f"[错误] 从备份恢复失败: {restore_e}")
            
            # 如果无法恢复，抛出异常而不是返回空列表
            raise RuntimeError(f"JSON解析失败且无法从备份恢复: {path}")
            
        except Exception as e:
            print(f"[错误] 读取文件失败: {e}")
            # 对于其他异常，也抛出而不是返回空列表
            raise RuntimeError(f"读取文件失败: {e}")

def save_json(path, data):
    """安全保存JSON文件"""
    # 获取文件锁
    lock = file_lock_manager.acquire_lock(str(path))
    with lock:
        try:
            # 验证数据
            if not validate_json_data(data):
                raise ValueError("要保存的数据格式无效")
            
            # 确保目录存在
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 原子性写入
            atomic_write_json(path, data)
            
        except Exception as e:
            print(f"[错误] 保存文件失败: {e}")
            # 尝试创建紧急备份
            try:
                emergency_backup = path.with_suffix(f'.emergency_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                with open(emergency_backup, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"[紧急备份] 已创建紧急备份: {emergency_backup}")
            except Exception as backup_e:
                print(f"[严重错误] 紧急备份也失败: {backup_e}")
            raise

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

def detect_website_type(url: str) -> str:
    """检测网站类型"""
    if "mp.weixin.qq.com" in url:
        return "wechat"
    elif "toutiao.com" in url or "m.toutiao.com" in url:
        return "toutiao"
    elif "163.com" in url:
        return "netease"
    elif "sina.com.cn" in url or "sina.cn" in url:
        return "sina"
    elif "sohu.com" in url:
        return "sohu"
    elif "qq.com" in url and "news" in url:
        return "qq_news"
    elif "ifeng.com" in url:
        return "ifeng"
    elif "cls.cn" in url or "cailianpress" in url:
        return "cailianpress"
    else:
        return "unknown"

def is_article_deleted_or_unavailable(soup: BeautifulSoup) -> bool:
    """检查文章是否已删除或不可访问"""
    import re
    
    # 获取页面文本内容
    page_text = soup.get_text().lower()
    
    # 微信文章删除的常见提示
    wechat_deleted_indicators = [
        "该内容已被发布者删除",
        "内容已被删除",
        "文章已被删除",
        "该文章已被删除",
        "内容不存在",
        "文章不存在",
        "该内容不存在",
        "抱歉，该内容已被删除",
        "抱歉，文章已被删除",
        "该内容已被发布者删除",
        "内容已被发布者删除",
        "文章已被发布者删除",
        "该文章已被发布者删除",
        "内容已删除",
        "文章已删除",
        "该内容已删除",
        "该文章已删除",
        "内容不存在或已被删除",
        "文章不存在或已被删除",
        "该内容不存在或已被删除",
        "该文章不存在或已被删除"
    ]
    
    # 通用删除提示
    general_deleted_indicators = [
        "404",
        "not found",
        "页面不存在",
        "页面已删除",
        "内容已删除",
        "文章已删除",
        "内容不存在",
        "文章不存在",
        "页面不存在或已被删除",
        "内容不存在或已被删除",
        "文章不存在或已被删除",
        "该页面不存在",
        "该内容不存在",
        "该文章不存在",
        "页面已失效",
        "内容已失效",
        "文章已失效",
        "链接已失效",
        "页面已过期",
        "内容已过期",
        "文章已过期"
    ]
    
    # 检查微信特定的删除提示
    for indicator in wechat_deleted_indicators:
        if indicator in page_text:
            print(f"[检测] 发现删除提示: {indicator}")
            return True
    
    # 检查通用删除提示
    for indicator in general_deleted_indicators:
        if indicator in page_text:
            print(f"[检测] 发现删除提示: {indicator}")
            return True
    
    # 检查页面标题中的删除提示
    title_tag = soup.find("title")
    if title_tag:
        title_text = title_tag.get_text().lower()
        for indicator in wechat_deleted_indicators + general_deleted_indicators:
            if indicator in title_text:
                print(f"[检测] 标题中发现删除提示: {indicator}")
                return True
    
    # 检查特定HTML元素中的删除提示
    error_elements = soup.find_all(["div", "p", "span", "h1", "h2", "h3"], 
                                  class_=re.compile(r"error|deleted|not-found|404|unavailable", re.I))
    
    for element in error_elements:
        element_text = element.get_text().lower()
        for indicator in wechat_deleted_indicators + general_deleted_indicators:
            if indicator in element_text:
                print(f"[检测] HTML元素中发现删除提示: {indicator}")
                return True
    
    # 检查页面是否为空或内容过少
    content_length = len(page_text.strip())
    
    # 检查是否包含正常的文章内容
    article_indicators = [
        "js_content",  # 微信文章内容容器
        "article-content",
        "content",
        "article",
        "post",
        "entry"
    ]
    
    has_article_content = False
    for indicator in article_indicators:
        if soup.find(attrs={"id": indicator}) or soup.find(attrs={"class": re.compile(indicator, re.I)}):
            has_article_content = True
            break
    
    # 如果找到了文章内容容器，即使内容较少也认为是正常文章
    if has_article_content:
        return False
    
    # 如果没有找到文章内容容器且内容过少，可能是删除页面
    if content_length < 200:  # 提高阈值，避免误判
        print(f"[检测] 未找到文章内容容器且内容过少({content_length}字符)，可能是删除页面")
        return True
    
        return False

def is_valid_article_content(article_data: dict) -> bool:
    """检查文章内容是否有效"""
    if not article_data:
        return False
    
    # 检查标题是否有效
    title = article_data.get('title', '').strip()
    if not title or title in ['无标题', '文章标题', '微信文章标题', '微信公众号文章标题']:
        print(f"[验证] 标题无效: '{title}'")
        return False
    
    # 检查内容是否有效
    content = article_data.get('content', '').strip()
    if not content or len(content) < 30:  # 内容太短（降低阈值）
        print(f"[验证] 内容无效或过短: {len(content)} 字符")
        return False
    
    # 检查是否包含占位符内容
    placeholder_content = [
        "文章围绕某一主题展开",
        "作者通过分析数据",
        "文章强调了",
        "内容逻辑清晰",
        "具有较强的参考价值",
        "文章正文内容通过Markdown格式",
        "重点阐述了核心观点",
        "旨在为读者提供"
    ]
    
    for placeholder in placeholder_content:
        if placeholder in content:
            print(f"[验证] 内容包含占位符: '{placeholder}'")
            return False
    
    return True

def extract_wechat_article(soup: BeautifulSoup) -> dict:
    """提取微信公众号文章"""
    # 检查文章是否已删除或不可访问
    if is_article_deleted_or_unavailable(soup):
        print("[警告] 文章已删除或不可访问")
        return None
    
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
        print("[警告] 找不到正文")
        return None
    
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.bypass_tables = False
    body_md = h.handle(str(content_div))
    
    return {
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "content": body_md
    }

def extract_toutiao_article(soup: BeautifulSoup) -> dict:
    """提取头条文章"""
    # 检查文章是否已删除或不可访问
    if is_article_deleted_or_unavailable(soup):
        print("[警告] 文章已删除或不可访问")
        return None
    
    import re
    
    # 提取标题
    title = "无标题"
    title_selectors = [
        "h1.article-title",
        "h1.title",
        ".article-title",
        ".title",
        "h1",
        ".headline"
    ]
    
    for selector in title_selectors:
        title_tag = soup.select_one(selector)
        if title_tag:
            title = title_tag.get_text(strip=True)
            if title and len(title) > 5:
                break
    
    # 提取作者
    author = "未知作者"
    author_selectors = [
        ".author-name",
        ".author",
        ".byline",
        ".source",
        ".media-name",
        "[data-author]"
    ]
    
    for selector in author_selectors:
        author_tag = soup.select_one(selector)
        if author_tag:
            author = author_tag.get_text(strip=True)
            if author and len(author) > 1:
                break
    
    # 提取时间
    publish_time = ""
    time_selectors = [
        ".time",
        ".publish-time",
        ".date",
        ".timestamp",
        "[data-time]"
    ]
    
    for selector in time_selectors:
        time_tag = soup.select_one(selector)
        if time_tag:
            time_text = time_tag.get_text(strip=True)
            # 增强时间解析：如果时间字段包含作者信息，尝试分离
            if "记者" in time_text or "责编" in time_text or "编辑" in time_text:
                # 提取纯时间部分
                time_patterns = [
                    r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',  # 2025-07-28 16:26
                    r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})',  # 2025/07/28 16:26
                    r'(\d{2}-\d{2}\s+\d{2}:\d{2})',        # 07-28 16:26
                    r'(\d{2}:\d{2})'                        # 16:26
                ]
                
                for pattern in time_patterns:
                    time_match = re.search(pattern, time_text)
                    if time_match:
                        publish_time = time_match.group(1)
                        break
            else:
                # 普通时间格式检查
                if re.search(r'\d{4}-\d{2}-\d{2}|\d{2}-\d{2}|\d{2}:\d{2}', time_text):
                    publish_time = time_text
            
            if publish_time:
                break
    
    # 提取正文
    content = ""
    content_selectors = [
        ".article-content",
        ".content",
        ".article-body",
        ".body",
        ".text",
        ".article-text"
    ]
    
    for selector in content_selectors:
        content_div = soup.select_one(selector)
        if content_div:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.bypass_tables = False
            content = h.handle(str(content_div))
            if content and len(content) > 100:
                break
    
    # 如果还是找不到内容，尝试更通用的方法
    if not content:
        # 查找包含大量文本的div
        text_divs = soup.find_all("div")
        for div in text_divs:
            text = div.get_text(strip=True)
            if len(text) > 200 and not any(skip in text.lower() for skip in ['copyright', '版权所有', '广告', 'advertisement']):
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.bypass_tables = False
                content = h.handle(str(div))
                break
    
    return {
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "content": content
    }

def extract_generic_article(soup: BeautifulSoup) -> dict:
    """通用文章提取方法"""
    # 检查文章是否已删除或不可访问
    if is_article_deleted_or_unavailable(soup):
        print("[警告] 文章已删除或不可访问")
        return None
    
    import re
    
    # 提取标题
    title = "无标题"
    title_selectors = [
        "h1",
        ".title",
        ".headline",
        ".article-title",
        "title"
    ]
    
    for selector in title_selectors:
        title_tag = soup.select_one(selector)
        if title_tag:
            title = title_tag.get_text(strip=True)
            if title and len(title) > 5:
                break
    
    # 提取作者
    author = "未知作者"
    author_selectors = [
        ".author",
        ".byline",
        ".writer",
        ".source",
        ".media-name",
        "[data-author]"
    ]
    
    for selector in author_selectors:
        author_tag = soup.select_one(selector)
        if author_tag:
            author = author_tag.get_text(strip=True)
            if author and len(author) > 1:
                break
    
    # 提取时间
    publish_time = ""
    time_selectors = [
        ".time",
        ".date",
        ".publish-time",
        ".timestamp",
        ".created-time",
        "[data-time]"
    ]
    
    for selector in time_selectors:
        time_tag = soup.select_one(selector)
        if time_tag:
            time_text = time_tag.get_text(strip=True)
            # 增强时间解析：如果时间字段包含作者信息，尝试分离
            if "记者" in time_text or "责编" in time_text or "编辑" in time_text:
                # 提取纯时间部分
                time_patterns = [
                    r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',  # 2025-07-28 16:26
                    r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})',  # 2025/07/28 16:26
                    r'(\d{2}-\d{2}\s+\d{2}:\d{2})',        # 07-28 16:26
                    r'(\d{2}:\d{2})'                        # 16:26
                ]
                
                for pattern in time_patterns:
                    time_match = re.search(pattern, time_text)
                    if time_match:
                        publish_time = time_match.group(1)
                        break
            else:
                # 普通时间格式检查
                if re.search(r'\d{4}-\d{2}-\d{2}|\d{2}-\d{2}|\d{2}:\d{2}', time_text):
                    publish_time = time_text
            
            if publish_time:
                break
    
    # 提取正文
    content = ""
    content_selectors = [
        ".article-content",
        ".content",
        ".article-body",
        ".body",
        ".text",
        ".article-text",
        ".main-content",
        ".post-content"
    ]
    
    for selector in content_selectors:
        content_div = soup.select_one(selector)
        if content_div:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.bypass_tables = False
            content = h.handle(str(content_div))
            if content and len(content) > 100:
                break
    
    # 如果还是找不到内容，尝试查找包含最多文本的div
    if not content:
        text_divs = soup.find_all("div")
        max_text_length = 0
        best_div = None
        
        for div in text_divs:
            text = div.get_text(strip=True)
            if len(text) > max_text_length and len(text) > 200:
                # 排除导航、广告等
                if not any(skip in text.lower() for skip in ['copyright', '版权所有', '广告', 'advertisement', '导航', 'menu']):
                    max_text_length = len(text)
                    best_div = div
        
        if best_div:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.bypass_tables = False
            content = h.handle(str(best_div))
    
    return {
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "content": content
    }

def extract_cailianpress_article(soup: BeautifulSoup) -> dict:
    """提取财联社文章"""
    # 检查文章是否已删除或不可访问
    if is_article_deleted_or_unavailable(soup):
        print("[警告] 文章已删除或不可访问")
        return None
    
    import re
    
    # 提取标题
    title = "无标题"
    title_selectors = [
        "h1.article-title",
        "h1.title",
        ".article-title",
        ".title",
        "h1",
        ".headline",
        ".article-headline"
    ]
    
    for selector in title_selectors:
        title_tag = soup.select_one(selector)
        if title_tag:
            title = title_tag.get_text(strip=True)
            if title and len(title) > 5:
                break
    
    # 提取作者和时间（财联社的特殊处理）
    author = "未知作者"
    publish_time = ""
    
    # 财联社的作者和时间通常在同一个元素中，需要分离
    author_time_selectors = [
        ".article-info",
        ".article-meta",
        ".meta-info",
        ".publish-info",
        ".author-time",
        ".byline"
    ]
    
    for selector in author_time_selectors:
        meta_tag = soup.select_one(selector)
        if meta_tag:
            meta_text = meta_tag.get_text(strip=True)
            
            # 尝试分离作者和时间
            # 财联社格式通常是: "财联社记者 高艳云责编 李桂芳2025-07-28 16:26"
            # 或者: "财联社记者 高艳云 2025-07-28 16:26"
            
            # 查找时间模式
            time_patterns = [
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',  # 2025-07-28 16:26
                r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})',  # 2025-07-28 16:26
                r'(\d{2}-\d{2}\s+\d{2}:\d{2})',        # 07-28 16:26
                r'(\d{2}:\d{2})'                        # 16:26
            ]
            
            for pattern in time_patterns:
                time_match = re.search(pattern, meta_text)
                if time_match:
                    publish_time = time_match.group(1)
                    # 从元信息中移除时间部分，剩下的就是作者信息
                    author_part = re.sub(pattern, '', meta_text).strip()
                    if author_part:
                        # 清理作者信息，移除常见的无关词汇
                        author_part = re.sub(r'财联社记者\s*', '', author_part)
                        author_part = re.sub(r'责编\s*', '', author_part)
                        author_part = re.sub(r'编辑\s*', '', author_part)
                        author_part = re.sub(r'记者\s*', '', author_part)
                        author_part = author_part.strip()
                        
                        # 如果作者信息包含多个名字，只取第一个
                        if author_part:
                            # 进一步清理：移除"责编"等词汇
                            author_part = re.sub(r'责编\s*', '', author_part)
                            author_part = re.sub(r'编辑\s*', '', author_part)
                            author_part = re.sub(r'记者\s*', '', author_part)
                            author_part = author_part.strip()
                            
                            # 分割多个作者名字（通常用空格或特殊字符分隔）
                            author_names = re.split(r'\s+|[、，,，]', author_part)
                            
                            # 如果分割后只有一个元素且包含多个中文字符，尝试按字符分割
                            if len(author_names) == 1 and len(author_names[0]) > 3:
                                # 尝试按2-3个字符分割（中文名字通常是2-3个字符）
                                long_name = author_names[0]
                                # 按2个字符分割
                                split_names = [long_name[i:i+2] for i in range(0, len(long_name), 2)]
                                # 取第一个有效的名字（2-3个字符）
                                for name in split_names:
                                    if len(name) >= 2 and len(name) <= 3:
                                        author = name
                                        break
                            else:
                                # 取第一个非空的名字
                                for name in author_names:
                                    name = name.strip()
                                    if name and len(name) > 1 and not name in ['记者', '责编', '编辑']:
                                        author = name
                                        break
                    break
            
            if publish_time:
                break
    
    # 如果上面的方法没有找到，尝试单独查找作者和时间
    if not author or author == "未知作者":
        author_selectors = [
            ".author-name",
            ".author",
            ".writer",
            ".reporter",
            "[data-author]"
        ]
        
        for selector in author_selectors:
            author_tag = soup.select_one(selector)
            if author_tag:
                author_text = author_tag.get_text(strip=True)
                if author_text and len(author_text) > 1:
                    author = author_text
                    break
    
    if not publish_time:
        time_selectors = [
            ".publish-time",
            ".time",
            ".date",
            ".timestamp",
            ".article-time",
            "[data-time]"
        ]
        
        for selector in time_selectors:
            time_tag = soup.select_one(selector)
            if time_tag:
                time_text = time_tag.get_text(strip=True)
                # 检查是否包含时间格式
                if re.search(r'\d{4}-\d{2}-\d{2}|\d{2}-\d{2}|\d{2}:\d{2}', time_text):
                    publish_time = time_text
                    break
    
    # 提取正文
    content = ""
    content_selectors = [
        ".article-content",
        ".content",
        ".article-body",
        ".body",
        ".text",
        ".article-text",
        ".main-content"
    ]
    
    for selector in content_selectors:
        content_div = soup.select_one(selector)
        if content_div:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.bypass_tables = False
            content = h.handle(str(content_div))
            if content and len(content) > 100:
                break
    
    # 如果还是找不到内容，尝试查找包含最多文本的div
    if not content:
        text_divs = soup.find_all("div")
        max_text_length = 0
        best_div = None
        
        for div in text_divs:
            text = div.get_text(strip=True)
            if len(text) > max_text_length and len(text) > 200:
                # 排除导航、广告等
                if not any(skip in text.lower() for skip in ['copyright', '版权所有', '广告', 'advertisement', '导航', 'menu']):
                    max_text_length = len(text)
                    best_div = div
        
        if best_div:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.bypass_tables = False
            content = h.handle(str(best_div))
    
    # 清理和验证字段
    if not author or author == "未知作者":
        author = "财联社"
    
    # 验证时间格式
    if publish_time:
        # 如果时间包含作者信息，尝试清理
        if "记者" in publish_time or "责编" in publish_time:
            # 提取纯时间部分
            time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}|\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}|\d{2}-\d{2}\s+\d{2}:\d{2}|\d{2}:\d{2})', publish_time)
            if time_match:
                publish_time = time_match.group(1)
    
    return {
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "content": content
    }


def extract_article_with_ai(html_content: str, url: str) -> dict:
    """使用AI解析文章内容"""
    try:
        print("[AI解析] 使用AI解析文章内容...")
        
        # 首先检查HTML内容是否包含删除提示
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        if is_article_deleted_or_unavailable(soup):
            print("[AI解析] 检测到文章已删除或不可访问，跳过AI解析")
            return None
        
        # 构建AI提示词
        prompt = f"""你是一个专业的网页内容解析助手。请从以下HTML页面中提取文章的实际内容信息。

页面URL: {url}

请仔细分析HTML内容，提取以下信息：
1. 文章的实际标题（不是页面标题或默认值）
2. 文章的实际作者（不是"作者名称"等默认值）
3. 文章的实际发表时间
4. 文章的实际正文内容

HTML内容（前5000字符）:
{html_content[:5000]}

请严格按照以下JSON格式返回，不要添加任何解释或评论：
{{
    "title": "实际文章标题",
    "author": "实际作者姓名", 
    "publish_time": "实际发表时间",
    "content": "实际文章正文内容（转换为Markdown格式）"
}}

重要提示：
- 不要输出"文章标题"、"作者名称"、"发表时间"等占位符
- 不要评价代码或HTML结构
- 只提取实际的文章内容信息
- 如果某个信息无法找到，使用"未知"或空字符串
- 直接返回JSON，不要包含任何其他文字

结果：/no_think"""

        messages = [
            {
                'role': 'system',
                'content': '你是一个专业的网页内容解析助手。你的任务是提取网页中的实际文章内容，包括标题、作者、时间和正文。不要评价代码或HTML结构，只提取实际的文章信息。'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        
        ai_response = chat_with_ai(messages)
        
        # 清理AI响应
        ai_response = _clean_ai_response(ai_response)
        
        # 尝试解析JSON
        try:
            # 查找JSON部分
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                # 验证必要字段
                required_fields = ['title', 'author', 'publish_time', 'content']
                for field in required_fields:
                    if field not in result:
                        result[field] = "未知" if field != 'content' else ""
                
                print("[AI解析] 成功解析文章内容")
                return result
            else:
                print("[AI解析] 无法从AI响应中提取JSON")
                return None
                
        except json.JSONDecodeError as e:
            print(f"[AI解析] JSON解析失败: {e}")
            return None
            
    except Exception as e:
        print(f"[AI解析] AI解析失败: {e}")
        return None

def fetch_article(url: str, sess: requests.Session, original_title: str = None) -> dict | None:
    """获取文章内容 - 支持多种网站"""
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
    
    # 检测网站类型
    website_type = detect_website_type(url)
    print(f"[解析] 检测到网站类型: {website_type}")
    
    # 根据网站类型选择解析方法
    article_data = None
    
    if website_type == "wechat":
        article_data = extract_wechat_article(soup)
    elif website_type == "toutiao":
        article_data = extract_toutiao_article(soup)
    elif website_type == "cailianpress":
        article_data = extract_cailianpress_article(soup)
    else:
        # 对于未知网站，先尝试通用解析
        article_data = extract_generic_article(soup)
    
    # 如果规则解析失败，使用AI解析
    if not article_data or not article_data.get('content') or len(article_data.get('content', '')) < 50:
        print("[规则解析] 规则解析失败或内容不足，尝试AI解析...")
        ai_article_data = extract_article_with_ai(resp.text, url)
        if ai_article_data and ai_article_data.get('content'):
            print("[AI解析] AI解析成功")
            article_data = ai_article_data
        else:
            print("[AI解析] AI解析也失败")
    
    # 最终验证
    if not article_data:
        print("[错误] 无法解析文章内容")
        return None
    
    # 验证文章内容是否有效
    if not is_valid_article_content(article_data):
        print("[错误] 文章内容验证失败，跳过此文章")
        return None
    
    # 标题处理：优先使用原始标题，如果解析的标题有问题则使用原始标题
    parsed_title = article_data.get('title', '')
    
    # 检查解析的标题是否有问题
    def is_bad_title(title):
        """检查标题是否有问题"""
        if not title or len(title.strip()) == 0:
            return True
        
        # 检查是否是默认值或错误值
        bad_titles = [
            "无标题", "文章标题", "微信文章标题", "微信公众号文章标题",
            "title", "Title", "TITLE", "标题", "文章", "Article"
        ]
        
        if title.strip() in bad_titles:
            return True
        
        # 检查是否包含编码问题（乱码）
        try:
            # 尝试编码解码，如果失败可能是乱码
            title.encode('utf-8').decode('utf-8')
        except UnicodeError:
            return True
        
        # 检查是否包含大量特殊字符或数字（可能是编码问题）
        if len(title) > 10 and sum(1 for c in title if c.isascii() and not c.isalnum()) > len(title) * 0.3:
            return True
        
        return False
    
    # 如果解析的标题有问题且有原始标题，使用原始标题
    if is_bad_title(parsed_title) and original_title:
        print(f"[标题修正] 解析标题有问题: '{parsed_title}'，使用原始标题: '{original_title}'")
        article_data['title'] = original_title
    elif is_bad_title(parsed_title):
        print(f"[标题警告] 解析标题有问题且无原始标题: '{parsed_title}'")
        article_data['title'] = "无标题"
    
    # 确保所有必要字段都存在
    if not article_data.get('author'):
        article_data['author'] = "未知作者"
    if not article_data.get('publish_time'):
        article_data['publish_time'] = ""
    if not article_data.get('content'):
        article_data['content'] = ""
    
    # 添加URL字段
    article_data['url'] = url
    
    print(f"[解析] 成功解析文章: {article_data['title']}")
    print(f"[解析] 作者: {article_data['author']}")
    print(f"[解析] 时间: {article_data['publish_time']}")
    print(f"[解析] 内容长度: {len(article_data['content'])} 字符")
    
    return article_data

# --- AI摘要生成 ---
# 直接import file_reader.py中的FileReader
sys.path.insert(0, str(Path(__file__).parent))
from tidyfile.core.file_reader import FileReader

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
    
    # 直接保存文章数据（不需要包装为列表）
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(article_json, f, ensure_ascii=False, indent=2)
        print(f"[保存] 文章数据已保存: {file_path}")
    except Exception as e:
        print(f"[错误] 保存文章数据失败: {e}")
        raise
    
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

def _clean_ai_response(response: str) -> str:
    """清理AI响应中的思考过程"""
    if not response:
        return response
    
    # 清理可能的思考过程标签和内容
    response = response.replace('<think>', '').replace('</think>', '').strip()
    
    # 移除常见的思考过程开头
    think_prefixes = [
        '好的，', '好，', '嗯，', '我来', '我需要', '首先，', '让我', '现在我要',
        '用户希望', '用户要求', '用户让我', '根据', '基于', '考虑到', '让我先仔细看看',
        '用户给了我这个查询', '用户给了我这个任务', '用户给了一个任务',
        '首先，我得看一下', '首先，我要理解', '首先，我得仔细看看',
        '好的，用户让我', '用户让我生成', '内容来自文件', '重点包括', '首先，我需要确认'
    ]
    
    # 更激进的清理：移除所有以思考过程开头的句子
    lines = response.split('\n')
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
        sentences = response.split('。')
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
    
    # 如果还是没有内容，使用原始响应的最后一部分
    if not cleaned_lines:
        # 取最后100个字符
        response = response[-100:] if len(response) > 100 else response
        return response
    
    # 重新组合清理后的内容
    if cleaned_lines:
        response = '\n'.join(cleaned_lines)
    
    return response.strip()

def safe_append_record(ai_results, new_record, max_retries=3):
    """安全地追加记录到AI结果列表"""
    for attempt in range(max_retries):
        try:
            # 验证新记录（只验证微信文章记录格式）
            if not validate_wechat_article_record(new_record):
                raise ValueError("新记录格式无效")
            
            # 追加记录
            ai_results.append(new_record)
            
            # 保存到文件
            save_json(AI_RESULT_JSON, ai_results)
            
            print(f"[成功] 记录已安全追加并保存")
            return True
            
        except Exception as e:
            print(f"[错误] 第{attempt + 1}次尝试追加记录失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)  # 等待1秒后重试
            else:
                print(f"[严重错误] 追加记录最终失败，尝试紧急保存")
                # 紧急保存：直接写入文件
                try:
                    with open(AI_RESULT_JSON, 'w', encoding='utf-8') as f:
                        json.dump(ai_results, f, ensure_ascii=False, indent=2)
                    print(f"[紧急保存] 成功")
                    return True
                except Exception as emergency_e:
                    print(f"[严重错误] 紧急保存也失败: {emergency_e}")
                    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary_length', type=int, default=200, help='AI摘要长度')
    args = parser.parse_args()
    summary_length = args.summary_length
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 启动微信文章AI摘要生成脚本，摘要长度：{summary_length}")
    print(f"[配置] 文章文件: {ARTICLE_JSON}")
    print(f"[配置] 输出文件: {AI_RESULT_JSON}")
    print(f"[配置] 文章目录: {ARTICLES_DIR}")
    
    if not ARTICLE_JSON.exists():
        print(f"[错误] 未找到 {ARTICLE_JSON}，请先备份收藏文章！")
        return
    
    print(f"[加载] 正在加载微信文章数据...")
    articles = load_json(ARTICLE_JSON)
    if not articles:
        print("[错误] 没有可处理的微信文章记录！")
        return
    
    print(f"[加载] 成功加载 {len(articles)} 篇微信文章")
    
    print(f"[加载] 正在加载AI结果文件...")
    
    # 首先等待文件写入完成
    if not wait_for_file_stable(AI_RESULT_JSON):
        print(f"[错误] 文件写入超时，无法安全加载: {AI_RESULT_JSON}")
        print(f"[建议] 请检查是否有其他进程正在写入该文件")
        return
    
    try:
        ai_results = load_json(AI_RESULT_JSON)
        print(f"[加载] 成功加载 {len(ai_results)} 条AI分析记录")
    except RuntimeError as e:
        print(f"[严重错误] 无法安全加载AI结果文件: {e}")
        print(f"[建议] 请检查文件是否正在被其他进程写入，或等待写入完成后再运行")
        print(f"[建议] 如果问题持续，请检查备份文件: {AI_RESULT_JSON.with_suffix('.backup_*.json')}")
        return
    except Exception as e:
        print(f"[严重错误] 加载AI结果文件时发生未知错误: {e}")
        return
    
    # 创建已存在文章的集合（基于标题和链接）
    exist_articles = set()
    for item in ai_results:
        title = item.get('文章标题', '').strip()
        url = item.get('源文件路径', '').strip()
        if title and url:
            exist_articles.add((title, url))
    
    print(f"[去重] 检测到 {len(exist_articles)} 篇已处理文章")
    
    # 统计信息初始化
    total_articles = len(articles)
    processed_count = 0
    successful_count = 0
    failed_count = 0
    skipped_count = 0
    new_records = []
    
    print(f"\n=== 微信文章AI摘要生成任务 ===")
    print(f"总文章数: {total_articles}")
    print(f"已存在文章数: {len(exist_articles)}")
    print(f"待处理文章数: {total_articles - len(exist_articles)}")
    print(f"摘要长度: {summary_length} 字符")
    print("=" * 50)
    
    print(f"[初始化] 正在初始化网络会话...")
    sess = build_session()
    print(f"[初始化] 网络会话初始化完成")
    
    for idx, art in enumerate(articles, 1):
        title = art.get('文章标题', '').strip()
        url = art.get('源文件路径', '').strip()
        
        if not title or not url:
            failed_count += 1
            print(f"[{idx}/{total_articles}] 文章信息不完整，跳过")
            continue
        
        # 检查文章是否已存在（基于标题和链接）
        if (title, url) in exist_articles:
            skipped_count += 1
            print(f"[{idx}/{total_articles}] 已存在，跳过：{title}")
            continue
        
        processed_count += 1
        progress = (idx / total_articles) * 100
        
        print(f"\n[{idx}/{total_articles}] 处理进度: {progress:.1f}%")
        print(f"当前处理: {title}")
        print(f"文章链接: {url}")
        
        # 获取文章内容
        article_data = fetch_article(url, sess, original_title=title)
        if not article_data:
            failed_count += 1
            print(f"[警告] 获取失败，跳过：{title}")
            continue
        
        # 保存文章内容到本地文件
        try:
            local_file_path = save_article_to_file(article_data)
            html_file_path = save_article_to_html(article_data)  # 新增：保存为HTML
            print(f"[保存] 文章内容已保存到：{local_file_path}")
            print(f"[保存] HTML文件已保存到：{html_file_path}")
        except Exception as e:
            failed_count += 1
            print(f"[错误] 保存文章失败：{e}")
            continue
        
        # AI生成摘要
        try:
            print(f"[AI] 正在生成摘要...")
            
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

摘要：/no_think"""

            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的文章摘要助手。重要：不要输出任何推理过程、思考步骤或解释。直接按要求输出结果。只输出摘要内容，不要包含任何其他信息。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
            
            summary_text = chat_with_ai(messages)
            # 清理AI响应中的思考过程
            summary_text = _clean_ai_response(summary_text)
            print(f"[AI] 摘要生成成功，长度: {len(summary_text)} 字符")
            
        except Exception as e:
            failed_count += 1
            print(f"[错误] AI摘要失败：{e}")
            continue
        
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record = {
            "处理时间": now_str,
            "文章标题": article_data['title'],  # fetch_article返回的是英文字段名
            "文章作者": article_data['author'],
            "发表时间": article_data['publish_time'],
            "文章摘要": summary_text,
            "源文件路径": url,
            "最匹配的目标目录": url,
            "最终目标路径": local_file_path
        }
        
        # 安全地追加记录
        if safe_append_record(ai_results, record):
            new_records.append(record)
            successful_count += 1
            print(f"[成功] 已生成摘要并追加：{title}")
        else:
            failed_count += 1
            print(f"[错误] 保存摘要记录失败：{title}")
        
        # 显示当前统计信息
        print(f"[统计] 成功: {successful_count}, 失败: {failed_count}, 跳过: {skipped_count}")
        
        time.sleep(random.uniform(*TIME_RANGE))
    
    # 最终统计报告
    print(f"\n" + "=" * 60)
    print(f"=== 微信文章AI摘要生成任务完成 ===")
    print(f"总文章数: {total_articles}")
    print(f"成功处理: {successful_count}")
    print(f"处理失败: {failed_count}")
    print(f"跳过文章: {skipped_count}")
    print(f"新增摘要: {len(new_records)}")
    
    if total_articles > 0:
        success_rate = (successful_count / (total_articles - skipped_count)) * 100 if (total_articles - skipped_count) > 0 else 0
        print(f"成功率: {success_rate:.1f}% (排除跳过的文章)")
    
    print(f"结果已保存到: {AI_RESULT_JSON}")
    print("=" * 60)

if __name__ == "__main__":
    main() 