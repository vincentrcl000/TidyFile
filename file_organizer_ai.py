#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能分类专用文件整理核心模块
"""
import os
import shutil
import logging
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
import ollama
from transfer_log_manager import TransferLogManager
import PyPDF2
import docx
import time

class FileOrganizerError(Exception):
    pass

class OllamaClient:
    def __init__(self, model_name: Optional[str] = None, host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host
        self.client = ollama.Client(host=host)
        self._validate_connection()
    def _validate_connection(self) -> None:
        try:
            models_response = self.client.list()
            if hasattr(models_response, 'models'):
                models_list = models_response.models
            elif isinstance(models_response, dict) and 'models' in models_response:
                models_list = models_response['models']
            else:
                models_list = models_response if isinstance(models_response, list) else []
            self.available_models = []
            for model in models_list:
                if isinstance(model, dict):
                    if 'name' in model:
                        model_name = model['name']
                        # 确保模型名称是字符串格式
                        if isinstance(model_name, str):
                            self.available_models.append(model_name)
                        else:
                            self.available_models.append(str(model_name))
                    elif 'model' in model:
                        model_name = model['model']
                        if isinstance(model_name, str):
                            self.available_models.append(model_name)
                        else:
                            self.available_models.append(str(model_name))
                elif isinstance(model, str):
                    self.available_models.append(model)
                else:
                    # 如果是其他类型，尝试提取model或name属性
                    model_name = None
                    if hasattr(model, 'model'):
                        model_name = getattr(model, 'model')
                    elif hasattr(model, 'name'):
                        model_name = getattr(model, 'name')
                    
                    if model_name:
                        if isinstance(model_name, str):
                            self.available_models.append(model_name)
                        else:
                            self.available_models.append(str(model_name))
                    else:
                        # 最后尝试直接转换为字符串
                        model_str = str(model)
                        # 如果字符串包含模型信息，尝试提取
                        if "model='" in model_str:
                            import re
                            match = re.search(r"model='([^']+)'", model_str)
                            if match:
                                self.available_models.append(match.group(1))
                            else:
                                self.available_models.append(model_str)
                        else:
                            self.available_models.append(model_str)
            if not self.available_models:
                raise FileOrganizerError("没有可用的模型，请先拉取模型")
            if self.model_name is None or self.model_name not in self.available_models:
                if self.model_name is not None:
                    logging.warning(f"模型 {self.model_name} 不可用，使用 {self.available_models[0]}")
                self.model_name = self.available_models[0]
                logging.info(f"自动选择模型: {self.model_name}")
            logging.info(f"成功连接到 Ollama，使用模型: {self.model_name}")
            logging.info(f"可用模型列表: {self.available_models}")
        except Exception as e:
            raise FileOrganizerError(f"连接 Ollama 失败: {e}")
    def chat_with_retry(self, messages: List[Dict], max_retries: Optional[int] = None) -> str:
        if max_retries is None:
            max_retries = len(self.available_models)
        last_error = None
        models_to_try = [self.model_name] + [m for m in self.available_models if m != self.model_name]
        for attempt, model_name in enumerate(models_to_try[:max_retries]):
            try:
                client = ollama.Client(host=self.host)
                if not isinstance(model_name, str) or not model_name:
                    raise FileOrganizerError("模型名无效，无法调用 chat")
                response = client.chat(
                    model=model_name,
                    messages=messages
                )
                if model_name != self.model_name:
                    logging.info(f"模型切换: {self.model_name} -> {model_name}")
                    self.model_name = model_name
                return response['message']['content'].strip()
            except Exception as e:
                last_error = e
                logging.warning(f"模型 {model_name} 响应失败: {e}")
                if attempt < max_retries - 1:
                    continue
        raise FileOrganizerError(f"所有可用模型都响应失败，最后错误: {last_error}")

class FileOrganizer:
    def __init__(self, model_name: Optional[str] = None, enable_transfer_log: bool = True):
        self.model_name = model_name
        self.ollama_client = None
        self.enable_transfer_log = enable_transfer_log
        self.transfer_log_manager = None
        
        # AI参数设置
        self.summary_length = 100  # 摘要长度，默认100字符
        self.content_truncate = 500  # 内容截取，默认500字符
        
        if self.enable_transfer_log:
            try:
                self.transfer_log_manager = TransferLogManager()
                logging.info("转移日志管理器初始化成功")
            except Exception as e:
                logging.warning(f"转移日志管理器初始化失败: {e}")
                self.enable_transfer_log = False
        self.setup_logging()
    def setup_logging(self) -> None:
        log_filename = f"file_organizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(os.path.dirname(__file__), "logs", log_filename)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        logging.info("文件整理器初始化完成")
    def initialize_ollama(self) -> None:
        try:
            self.ollama_client = OllamaClient(self.model_name)
            logging.info("Ollama 客户端初始化成功")
        except Exception as e:
            raise FileOrganizerError(f"初始化 Ollama 客户端失败: {e}")
    def scan_target_folders(self, target_directory: str) -> List[str]:
        try:
            target_path = Path(target_directory)
            if not target_path.exists():
                raise FileOrganizerError(f"目标目录不存在: {target_directory}")
            folders = []
            for item in target_path.rglob('*'):
                if item.is_dir():
                    relative_path = item.relative_to(target_path)
                    folders.append(str(relative_path))
            logging.info(f"扫描到 {len(folders)} 个目标文件夹（包含子目录）")
            return folders
        except Exception as e:
            raise FileOrganizerError(f"扫描目标文件夹失败: {e}")
    def get_directory_tree_structure(self, target_directory: str) -> str:
        try:
            target_path = Path(target_directory)
            if not target_path.exists():
                raise FileOrganizerError(f"目标目录不存在: {target_directory}")
            def build_tree(path: Path, prefix: str = "", is_last: bool = True) -> List[str]:
                lines = []
                if path != target_path:
                    connector = "└── " if is_last else "├── "
                    lines.append(f"{prefix}{connector}{path.name}")
                    prefix += "    " if is_last else "│   "
                subdirs = sorted([item for item in path.iterdir() if item.is_dir()], key=lambda x: x.name)
                for i, subdir in enumerate(subdirs):
                    is_last_subdir = (i == len(subdirs) - 1)
                    lines.extend(build_tree(subdir, prefix, is_last_subdir))
                return lines
            tree_lines = build_tree(target_path)
            tree_structure = "\n".join(tree_lines)
            logging.info(f"生成目录树结构，共 {len(tree_lines)} 行")
            return tree_structure
        except Exception as e:
            raise FileOrganizerError(f"生成目录树结构失败: {e}")
    def analyze_and_classify_file(self, file_path: str, target_directory: str) -> Dict[str, Any]:
        """
        新的文件分析和分类方法：先解析内容，生成摘要，再推荐目录
        返回包含提取内容、摘要和推荐目录的完整结果
        """
        start_time = time.time()
        timing_info = {}
        
        try:
            if not self.ollama_client:
                init_start = time.time()
                self.initialize_ollama()
                timing_info['ollama_init_time'] = round(time.time() - init_start, 3)
            
            file_name = Path(file_path).name
            logging.info(f"开始分析文件: {file_name}")
            
            # 第一步：解析文件内容
            extract_start = time.time()
            extracted_content = self._extract_file_content(file_path)
            extract_time = round(time.time() - extract_start, 3)
            timing_info['content_extraction_time'] = extract_time
            logging.info(f"文件内容提取完成，长度: {len(extracted_content)} 字符，耗时: {extract_time}秒")
            
            # 根据设置截取内容用于后续AI处理，提高处理效率
            truncate_length = self.content_truncate if self.content_truncate < 2000 else len(extracted_content)
            content_for_ai = extracted_content[:truncate_length] if extracted_content else ""
            if len(extracted_content) > truncate_length:
                logging.info(f"内容已截取至前{truncate_length}字符用于AI处理（原长度: {len(extracted_content)} 字符）")
            
            # 第二步：生成100字摘要（使用截取后的内容）
            summary_start = time.time()
            summary = self._generate_content_summary(content_for_ai, file_name)
            summary_time = round(time.time() - summary_start, 3)
            timing_info['summary_generation_time'] = summary_time
            logging.info(f"内容摘要生成完成: {summary[:50]}...，耗时: {summary_time}秒")
            
            # 第三步：推荐最匹配的存放目录（使用截取后的内容）
            recommend_start = time.time()
            recommended_folder, match_reason = self._recommend_target_folder(
                file_name, content_for_ai, summary, target_directory
            )
            recommend_time = round(time.time() - recommend_start, 3)
            timing_info['folder_recommendation_time'] = recommend_time
            
            total_time = round(time.time() - start_time, 3)
            timing_info['total_processing_time'] = total_time
            
            result = {
                'file_path': file_path,
                'file_name': file_name,
                'extracted_content': extracted_content,
                'content_summary': summary,
                'recommended_folder': recommended_folder,
                'match_reason': match_reason,
                'success': recommended_folder is not None,
                'timing_info': timing_info
            }
            
            if recommended_folder:
                logging.info(f"文件分析完成: {file_name} -> {recommended_folder}，总耗时: {total_time}秒")
                logging.info(f"摘要: {summary}")
                logging.info(f"推荐理由: {match_reason}")
                logging.info(f"详细耗时 - 内容提取: {extract_time}秒, 摘要生成: {summary_time}秒, 目录推荐: {recommend_time}秒")
            else:
                logging.warning(f"文件分析失败: {file_name}，总耗时: {total_time}秒")
            
            return result
            
        except Exception as e:
            total_time = round(time.time() - start_time, 3)
            timing_info['total_processing_time'] = total_time
            logging.error(f"文件分析失败: {e}，总耗时: {total_time}秒")
            return {
                'file_path': file_path,
                'file_name': Path(file_path).name,
                'extracted_content': '',
                'content_summary': '',
                'recommended_folder': None,
                'match_reason': f"分析失败: {str(e)}",
                'success': False,
                'error': str(e),
                'timing_info': timing_info
            }
    
    def classify_file(self, file_path: str, target_directory: str) -> tuple:
        """
        保持原有的分类方法兼容性
        """
        result = self.analyze_and_classify_file(file_path, target_directory)
        return result['recommended_folder'], result['match_reason'], result['success']
    def _build_classification_prompt(self, file_path: str, target_directory: str) -> str:
        file_name = Path(file_path).name
        file_extension = Path(file_path).suffix.lower()
        file_content = ""
        content_readable = False
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()[:2000]
                printable_ratio = sum(1 for c in file_content if c.isprintable() or c.isspace()) / len(file_content) if file_content else 0
                if printable_ratio > 0.7:
                    content_readable = True
                else:
                    file_content = "文件内容为二进制格式，无法读取"
        except Exception:
            for encoding in ['gbk', 'gb2312', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        file_content = f.read()[:2000]
                        printable_ratio = sum(1 for c in file_content if c.isprintable() or c.isspace()) / len(file_content) if file_content else 0
                        if printable_ratio > 0.7:
                            content_readable = True
                            break
                        else:
                            file_content = "文件内容为二进制格式，无法读取"
                except Exception:
                    continue
            if not content_readable:
                file_content = "无法读取文件内容"
        directory_structure = self.get_directory_tree_structure(target_directory)
        prompt = f"""
你是一个专业的文件分类助手。请阅读原文件的前500个字，或者识别第一页内容，根据文件内容判断文件应该归类到下列哪个文件夹中，注意，每个文件根据文件内容只匹配一个文件夹，匹配原则是：

- 优先匹配：文件内容主题和文件夹名及文件路径名最相符
- 降级匹配：如果读取不到文件内容，则用原文件名和目标文件夹名及文件夹路径名来匹配

文件信息：
- 原文件名：{file_name}
- 文件扩展名：{file_extension}
- 文件内容：{file_content if content_readable else "无法读取内容"}

目标目录文件夹清单如下：
{directory_structure}

输出格式要求：
原文件名|目标文件夹|匹配理由

其中匹配理由格式为：
内容匹配：{{用不多于20个字描述匹配理由}}
或者
无法读取内容，采用文件夹名匹配：{{用不多于20个字描述匹配理由}}

请严格按照上述格式输出，只输出一行结果。
"""
        return prompt
    
    def _extract_file_content(self, file_path: str, max_length: int = 3000) -> str:
        """
        提取文件内容（从file_reader.py复制的完整实现）
        
        Args:
            file_path: 文件路径
            max_length: 最大提取长度
            
        Returns:
            提取的文件内容
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise Exception(f"文件不存在: {file_path}")
            
            file_extension = file_path.suffix.lower()
            logging.info(f"正在提取文件内容: {file_path.name} (类型: {file_extension})")
            
            # 根据文件类型选择不同的提取方法
            if file_extension == '.pdf':
                return self._extract_pdf_content(file_path, max_length)
            elif file_extension in ['.docx', '.doc']:
                return self._extract_docx_content(file_path, max_length)
            elif file_extension in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv']:
                return self._extract_text_content(file_path, max_length)
            elif file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                return self._extract_image_info(file_path)
            else:
                # 尝试作为文本文件读取
                return self._extract_text_content(file_path, max_length)
                
        except Exception as e:
            logging.error(f"提取文件内容失败: {e}")
            return f"无法提取文件内容: {str(e)}"
    
    def _extract_pdf_content(self, file_path: Path, max_length: int) -> str:
        """
        提取PDF文件内容（从file_reader.py复制的完整实现）
        """
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                content = ""
                
                # 读取前几页内容
                for page_num in range(min(3, len(pdf_reader.pages))):
                    page = pdf_reader.pages[page_num]
                    content += page.extract_text() + "\n"
                    
                    if len(content) >= max_length:
                        break
                
                return content[:max_length] if content else "PDF文件内容为空或无法提取"
                
        except Exception as e:
            return f"PDF文件读取失败: {str(e)}"
    
    def _extract_docx_content(self, file_path: Path, max_length: int) -> str:
        """
        提取Word文档内容（从file_reader.py复制的完整实现）
        """
        try:
            # 检查文件是否存在且可读
            if not file_path.exists():
                return "文件不存在"
            
            if not file_path.is_file():
                return "路径不是文件"
            
            # 检查文件大小
            file_size = file_path.stat().st_size
            if file_size == 0:
                return "文件为空"
            
            # 尝试读取Word文档
            try:
                doc = docx.Document(file_path)
                content = ""
                
                # 提取段落内容
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():  # 跳过空段落
                        content += paragraph.text.strip() + "\n"
                        if len(content) >= max_length:
                            break
                
                # 如果段落内容为空，尝试提取表格内容
                if not content.strip():
                    for table in doc.tables:
                        for row in table.rows:
                            for cell in row.cells:
                                if cell.text.strip():
                                    content += cell.text.strip() + " "
                        content += "\n"
                        if len(content) >= max_length:
                            break
                
                return content[:max_length].strip() if content.strip() else "Word文档内容为空或无法提取"
                
            except Exception as docx_error:
                # 如果是.doc文件或损坏的.docx文件，尝试其他方法
                if file_path.suffix.lower() == '.doc':
                    return "不支持.doc格式，请转换为.docx格式"
                else:
                    return f"Word文档格式错误或文件损坏: {str(docx_error)}"
            
        except Exception as e:
            return f"Word文档读取失败: {str(e)}"
    
    def _extract_text_content(self, file_path: Path, max_length: int) -> str:
        """
        提取文本文件内容（从file_reader.py复制的完整实现）
        """
        try:
            # 尝试多种编码格式
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read(max_length)
                        
                        # 检查内容是否可读
                        printable_ratio = sum(1 for c in content if c.isprintable() or c.isspace()) / len(content) if content else 0
                        if printable_ratio > 0.7:
                            return content
                        
                except Exception:
                    continue
            
            return "文件内容为二进制格式，无法读取"
            
        except Exception as e:
            return f"文本文件读取失败: {str(e)}"
    
    def _extract_image_info(self, file_path: Path) -> str:
        """
        提取图片文件信息（从file_reader.py复制的完整实现）
        """
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                info = f"图片文件信息:\n"
                info += f"格式: {img.format}\n"
                info += f"尺寸: {img.size[0]} x {img.size[1]}\n"
                info += f"模式: {img.mode}\n"
                
                # 如果有EXIF信息，提取一些基本信息
                if hasattr(img, '_getexif') and img._getexif():
                    info += "包含EXIF信息\n"
                
                return info
                
        except Exception as e:
            return f"图片文件信息提取失败: {str(e)}"
    
    def _generate_content_summary(self, content: str, file_name: str) -> str:
        """
        生成文件内容摘要
        """
        try:
            if not content or content.startswith("无法") or content.startswith("文件内容为二进制"):
                return f"无法生成摘要：{content[:50]}..."
            
            if not self.ollama_client:
                self.initialize_ollama()
            
            prompt = f"""
请为以下文件内容生成一个{self.summary_length}字以内的中文摘要，要求：
1. 概括文件的主要内容和主题
2. 突出关键信息和要点
3. 语言简洁明了
4. 字数控制在{self.summary_length}字以内

文件名：{file_name}
文件内容：
{content}

请直接输出摘要内容，不要包含其他说明文字：
"""
            
            summary = self.ollama_client.chat_with_retry([
                {
                    'role': 'user',
                    'content': prompt
                }
            ])
            
            # 确保摘要长度不超过100字
            if len(summary) > 100:
                summary = summary[:97] + "..."
            
            return summary.strip()
            
        except Exception as e:
            logging.error(f"生成摘要失败: {e}")
            return f"摘要生成失败: {str(e)}"
    
    def _recommend_target_folder(self, file_name: str, content: str, summary: str, target_directory: str) -> tuple:
        """
        基于文件内容和摘要推荐最匹配的目标文件夹
        """
        try:
            if not self.ollama_client:
                self.initialize_ollama()
            
            target_folders = self.scan_target_folders(target_directory)
            directory_structure = self.get_directory_tree_structure(target_directory)
            
            # 判断是否有有效的内容和摘要
            has_valid_content = content and not content.startswith("无法") and not content.startswith("文件内容为二进制")
            has_valid_summary = summary and not summary.startswith("无法") and not summary.startswith("摘要生成失败")
            
            if has_valid_content and has_valid_summary:
                # 有内容和摘要时，优先使用摘要进行分类
                prompt = f"""
你是一个专业的文件分类助手。请根据文件的内容摘要，推荐最适合的存放文件夹。

文件信息：
- 文件名：{file_name}
- 内容摘要：{summary}

可选的目标文件夹：
{directory_structure}

分类原则：
1. 优先根据文件内容主题匹配文件夹
2. 考虑文件的用途和性质
3. 选择最具体、最相关的文件夹

输出格式：
文件名|推荐文件夹|推荐理由

推荐理由格式：
内容匹配：{{简述匹配原因，不超过30字}}

请严格按照格式输出一行结果：
"""
            else:
                # 无法获取有效内容时，使用文件名进行分类
                file_extension = Path(file_name).suffix.lower()
                prompt = f"""
你是一个专业的文件分类助手。由于无法读取文件内容，请根据文件名和扩展名推荐最适合的存放文件夹。

文件信息：
- 文件名：{file_name}
- 文件扩展名：{file_extension}
- 内容状态：{content[:100] if content else "无内容"}

可选的目标文件夹：
{directory_structure}

分类原则：
1. 根据文件扩展名匹配相应类型的文件夹
2. 根据文件名关键词匹配主题文件夹
3. 选择最具体、最相关的文件夹

输出格式：
文件名|推荐文件夹|推荐理由

推荐理由格式：
文件名匹配：{{简述匹配原因，不超过30字}}

请严格按照格式输出一行结果：
"""
            
            result = self.ollama_client.chat_with_retry([
                {
                    'role': 'user',
                    'content': prompt
                }
            ])
            
            return self._parse_classification_result(result, target_folders)
            
        except Exception as e:
            logging.error(f"推荐目标文件夹失败: {e}")
            return None, f"推荐失败: {str(e)}"
    def _parse_classification_result(self, result: str, target_folders: List[str]) -> tuple:
        try:
            result = result.strip()
            
            # 处理多行格式的结果，查找包含文件名和推荐信息的行
            lines = result.split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('---') or line.startswith('文件名|'):
                    continue
                
                parts = line.split('|')
                if len(parts) >= 3:
                    original_filename = parts[0].strip()
                    target_folder = parts[1].strip()
                    match_reason = parts[2].strip()
                    
                    # 验证目标文件夹是否有效
                    if target_folder in target_folders:
                        return target_folder, match_reason
                    else:
                        # 尝试模糊匹配
                        for valid_folder in target_folders:
                            if target_folder in valid_folder or valid_folder in target_folder:
                                return valid_folder, f"{match_reason}（模糊匹配：{target_folder}）"
                        
                        # 如果没有找到匹配的文件夹，继续尝试下一行
                        continue
            
            # 如果没有找到有效的分类结果，尝试原来的单行解析
            parts = result.split('|')
            if len(parts) >= 3:
                original_filename = parts[0].strip()
                target_folder = parts[1].strip()
                match_reason = parts[2].strip()
                
                if target_folder in target_folders:
                    return target_folder, match_reason
                else:
                    for valid_folder in target_folders:
                        if target_folder in valid_folder or valid_folder in target_folder:
                            return valid_folder, f"{match_reason}（模糊匹配：{target_folder}）"
            
            logging.warning(f"无法解析分类结果或找不到有效的目标文件夹: {result}")
            return None, None
            
        except Exception as e:
            logging.warning(f"解析分类结果失败: {e}, 原始结果: {result}")
            return None, None
    def scan_source_files(self, source_directory: str) -> List[str]:
        try:
            source_path = Path(source_directory)
            if not source_path.exists():
                raise FileOrganizerError(f"源目录不存在: {source_directory}")
            files = []
            for item in source_path.rglob('*'):
                if item.is_file():
                    files.append(str(item))
            logging.info(f"扫描到 {len(files)} 个待整理文件")
            return files
        except Exception as e:
            raise FileOrganizerError(f"扫描源文件失败: {e}")
    def scan_files(self, source_directory: str) -> List[Dict[str, object]]:
        try:
            source_path = Path(source_directory)
            if not source_path.exists():
                raise FileOrganizerError(f"源目录不存在: {source_directory}")
            files = []
            for item in source_path.rglob('*'):
                if item.is_file():
                    files.append({
                        'name': item.name,
                        'path': str(item),
                        'size': item.stat().st_size,
                        'extension': item.suffix.lower()
                    })
            logging.info(f"扫描到 {len(files)} 个待整理文件")
            return files
        except Exception as e:
            raise FileOrganizerError(f"扫描源文件失败: {e}")
    def get_target_folders(self, target_directory: str) -> List[str]:
        return self.scan_target_folders(target_directory)
    def preview_classification(self, source_directory: str, target_directory: str) -> List[Dict[str, object]]:
        try:
            source_files = self.scan_source_files(source_directory)
            if not source_files:
                raise FileOrganizerError("源目录中没有找到文件")
            preview_results = []
            logging.info(f"开始预览分类，共 {len(source_files)} 个文件，仅分析前10个")
            preview_count = min(10, len(source_files))
            for i, file_path in enumerate(source_files[:preview_count], 1):
                file_name = Path(file_path).name
                try:
                    logging.info(f"正在处理文件 {i}/{preview_count}: {file_name}")
                    # 使用新的分析方法
                    analysis_result = self.analyze_and_classify_file(file_path, target_directory)
                    
                    if analysis_result['success']:
                        timing_info = analysis_result.get('timing_info', {})
                        preview_results.append({
                            'file_path': file_path,
                            'file_name': file_name,
                            'target_folder': analysis_result['recommended_folder'],
                            'match_reason': analysis_result['match_reason'],
                            'classification_method': 'AI_Enhanced',
                            'success': True,
                            'extracted_content': analysis_result['extracted_content'][:200] + "..." if len(analysis_result['extracted_content']) > 200 else analysis_result['extracted_content'],
                            'content_summary': analysis_result['content_summary'],
                            'timing_info': timing_info
                        })
                        total_time = timing_info.get('total_processing_time', 0)
                        extract_time = timing_info.get('content_extraction_time', 0)
                        summary_time = timing_info.get('summary_generation_time', 0)
                        recommend_time = timing_info.get('folder_recommendation_time', 0)
                        
                        logging.info(f"文件 {file_name} 分析成功: {analysis_result['recommended_folder']} ({analysis_result['match_reason']})，总耗时: {total_time}秒")
                        logging.info(f"内容摘要: {analysis_result['content_summary']}")
                        logging.info(f"详细耗时 - 内容提取: {extract_time}秒, 摘要生成: {summary_time}秒, 目录推荐: {recommend_time}秒")
                    else:
                        timing_info = analysis_result.get('timing_info', {})
                        preview_results.append({
                            'file_path': file_path,
                            'file_name': file_name,
                            'target_folder': None,
                            'match_reason': analysis_result['match_reason'],
                            'classification_method': 'Failed',
                            'success': False,
                            'error': analysis_result.get('error', analysis_result['match_reason']),
                            'extracted_content': analysis_result.get('extracted_content', ''),
                            'content_summary': analysis_result.get('content_summary', ''),
                            'timing_info': timing_info
                        })
                        total_time = timing_info.get('total_processing_time', 0)
                        logging.warning(f"文件 {file_name} 分析失败: {analysis_result['match_reason']}，总耗时: {total_time}秒")
                except Exception as e:
                    error_msg = f"处理文件时出错: {str(e)}"
                    logging.error(f"文件 {file_name} 处理异常: {e}")
                    preview_results.append({
                        'file_path': file_path,
                        'file_name': file_name,
                        'target_folder': None,
                        'match_reason': error_msg,
                        'classification_method': 'Error',
                        'success': False,
                        'error': error_msg
                    })
            success_count = sum(1 for result in preview_results if result['success'])
            logging.info(f"预览分类完成，成功分类 {success_count}/{len(preview_results)} 个文件")
            return preview_results
        except Exception as e:
            raise FileOrganizerError(f"预览分类失败: {e}")
    def organize_file(self, file_path: str, target_directory: str, target_folders: List[str]) -> Tuple[bool, str]:
        try:
            if not self.ollama_client:
                self.initialize_ollama()
            file_path_obj = Path(file_path)
            filename = file_path_obj.name
            # recommended_folders = self.ollama_client.classify_file(filename, target_folders)
            target_folder, match_reason, success = self.classify_file(str(file_path_obj), target_directory)
            if not success or not target_folder:
                return False, "无法确定目标文件夹"
            # target_folder = recommended_folders[0]  # 已由上面获得
            target_folder_path = Path(target_directory) / target_folder
            target_folder_path.mkdir(parents=True, exist_ok=True)
            target_file_path = target_folder_path / filename
            if target_file_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    new_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                else:
                    new_filename = f"{filename}_{timestamp}"
                target_file_path = target_folder_path / new_filename
            shutil.copy2(file_path, target_file_path)
            logging.info(f"文件已复制: {file_path} -> {target_file_path}")
            return True, str(target_file_path)
        except Exception as e:
            error_msg = f"整理文件失败: {e}"
            logging.error(error_msg)
            return False, error_msg
    def organize_files(self, files=None, target_folders=None, target_base_dir=None, copy_mode=True, source_directory=None, target_directory=None, dry_run=False, progress_callback=None) -> Dict[str, object]:
        try:
            if source_directory and target_directory:
                target_folders = self.scan_target_folders(target_directory)
                files = self.scan_files(source_directory)
                target_base_dir = target_directory
                copy_mode = True
            if not files or not target_folders or not target_base_dir:
                raise FileOrganizerError("缺少必要参数")
            log_session_name = None
            if self.enable_transfer_log and self.transfer_log_manager and not dry_run:
                try:
                    session_name = f"organize_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    log_session_name = self.transfer_log_manager.start_transfer_session(session_name)
                    logging.info(f"开始转移日志会话: {session_name}")
                except Exception as e:
                    logging.warning(f"启动转移日志会话失败: {e}")
            if not target_folders:
                raise FileOrganizerError("目标目录中没有文件夹")
            if not files:
                raise FileOrganizerError("没有文件需要整理")
            results = {
                'total_files': len(files),
                'processed_files': 0,
                'successful_moves': 0,
                'failed_moves': 0,
                'skipped_files': 0,
                'success': [],
                'failed': [],
                'errors': [],
                'move_details': [],
                'ai_responses': [],
                'start_time': datetime.now(),
                'end_time': None,
                'transfer_log_file': log_session_name,
                'dry_run': dry_run
            }
            logging.info(f"开始安全文件整理，共 {len(files)} 个文件")
            print(f"\n=== 开始AI智能文件整理 ===")
            print(f"源目录: {source_directory if source_directory else '指定文件列表'}")
            print(f"目标目录: {target_base_dir}")
            print(f"待处理文件总数: {len(files)}")
            print(f"操作模式: {'复制' if copy_mode else '移动'}")
            print("=" * 50)
            
            for i, file_info in enumerate(files, 1):
                file_path = str(file_info['path'])
                filename = str(file_info['name'])
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(i, len(files), filename)
                
                # 控制台输出当前处理进度
                print(f"\n[{i}/{len(files)}] 正在处理: {filename}")
                
                try:
                    logging.info(f"正在处理文件 {i}/{len(files)}: {filename}")
                    print(f"  🔍 正在分析文件内容...", end="", flush=True)
                    target_folder, match_reason, success = self.classify_file(file_path, target_base_dir)
                    
                    results['ai_responses'].append({
                        'file_name': filename,
                        'target_folder': target_folder,
                        'match_reason': match_reason,
                        'success': success
                    })
                    
                    if not success or not target_folder:
                        error_msg = f"文件 {filename} 分类失败: {match_reason}，已跳过，未做任何处理"
                        print(f"\r  ❌ 分类失败: {match_reason}")
                        logging.warning(error_msg)
                        results['errors'].append(error_msg)
                        results['skipped_files'] += 1
                        results['failed'].append({
                            'source_path': file_path,
                            'error': error_msg
                        })
                        continue
                    
                    print(f"\r  ✅ 推荐目录: {target_folder}")
                    print(f"     理由: {match_reason}")
                    target_folder_path = Path(target_base_dir) / target_folder
                    if not target_folder_path.exists():
                        error_msg = f"目标文件夹不存在: {target_folder}"
                        logging.error(error_msg)
                        results['errors'].append(error_msg)
                        results['failed_moves'] += 1
                        results['failed'].append({
                            'source_path': file_path,
                            'error': error_msg
                        })
                        continue
                    original_target_path = target_folder_path / filename
                    target_file_path = original_target_path
                    if target_file_path.exists():
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        name_parts = filename.rsplit('.', 1)
                        if len(name_parts) == 2:
                            new_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                        else:
                            new_filename = f"{filename}_{timestamp}"
                        target_file_path = target_folder_path / new_filename
                        logging.info(f"文件名冲突，重命名为: {target_file_path.name}")
                    if not dry_run:
                        try:
                            if not Path(file_path).exists():
                                error_msg = f"源文件不存在: {file_path}"
                                logging.error(error_msg)
                                results['errors'].append(error_msg)
                                results['failed_moves'] += 1
                                results['failed'].append({
                                    'source_path': file_path,
                                    'error': error_msg
                                })
                                continue
                            if copy_mode:
                                shutil.copy2(file_path, str(target_file_path))
                                operation = "copy"
                                operation_cn = "复制"
                            else:
                                shutil.move(file_path, str(target_file_path))
                                operation = "move"
                                operation_cn = "移动"
                            if target_file_path.exists():
                                if not copy_mode and Path(file_path).exists():
                                    error_msg = f"文件移动验证失败: {filename}"
                                    logging.error(error_msg)
                                    results['errors'].append(error_msg)
                                    results['failed_moves'] += 1
                                    results['failed'].append({
                                        'source_path': file_path,
                                        'error': error_msg
                                    })
                                    continue
                                print(f"     ✅ {operation_cn}成功: {filename} -> {target_folder}")
                                logging.info(f"文件安全{operation_cn}成功: {filename} -> {target_folder} ({match_reason})")
                                results['successful_moves'] += 1
                            else:
                                error_msg = f"文件{operation_cn}验证失败: {filename}"
                                logging.error(error_msg)
                                results['errors'].append(error_msg)
                                results['failed_moves'] += 1
                                results['failed'].append({
                                    'source_path': file_path,
                                    'error': error_msg
                                })
                                continue
                        except Exception as move_error:
                            error_msg = f"{operation_cn}文件 {filename} 时出错: {move_error}"
                            logging.error(error_msg)
                            results['errors'].append(error_msg)
                            results['failed_moves'] += 1
                            results['failed'].append({
                                'source_path': file_path,
                                'error': error_msg
                            })
                            continue
                    else:
                        operation = "copy" if copy_mode else "move"
                        operation_cn = "复制" if copy_mode else "移动"
                        logging.info(f"[试运行] 文件将{operation_cn}: {filename} -> {target_folder} ({match_reason})")
                        results['successful_moves'] += 1
                    if self.enable_transfer_log and self.transfer_log_manager and not dry_run:
                        try:
                            file_size_raw = file_info.get('size', 0)
                            file_size = int(file_size_raw) if isinstance(file_size_raw, (int, float, str)) and str(file_size_raw).isdigit() else 0
                            self.transfer_log_manager.log_transfer_operation(
                                source_path=file_path,
                                target_path=str(target_file_path),
                                operation_type=operation,
                                target_folder=target_folder,
                                success=True,
                                file_size=file_size
                            )
                        except Exception as e:
                            logging.warning(f"记录转移日志失败: {e}")
                    results['success'].append({
                        'source_path': file_path,
                        'target_path': str(target_file_path),
                        'target_folder': target_folder,
                        'operation': operation
                    })
                    results['move_details'].append({
                        'source_file': file_path,
                        'file_name': filename,
                        'target_folder': target_folder,
                        'target_path': str(target_file_path),
                        'match_reason': match_reason,
                        'classification_method': 'AI',
                        'renamed': str(target_file_path) != str(original_target_path),
                        'operation': operation
                    })
                except Exception as e:
                    error_msg = f"处理文件 {filename} 时出现异常: {e}"
                    logging.error(error_msg)
                    results['errors'].append(error_msg)
                    results['failed_moves'] += 1
                    if self.enable_transfer_log and self.transfer_log_manager and not dry_run:
                        try:
                            operation_type = "copy" if copy_mode else "move"
                            self.transfer_log_manager.log_transfer_operation(
                                source_path=file_path,
                                target_path="",
                                operation_type=operation_type,
                                target_folder="",
                                success=False,
                                error_message=error_msg
                            )
                        except Exception as log_e:
                            logging.warning(f"记录失败转移日志失败: {log_e}")
                    results['failed'].append({
                        'source_path': file_path,
                        'error': error_msg
                    })
                finally:
                    results['processed_files'] += 1
            results['end_time'] = datetime.now()
            
            # 输出处理完成总结
            print(f"\n=== 文件整理完成 ===")
            print(f"总文件数: {results['total_files']}")
            print(f"成功处理: {results['successful_moves']} 个")
            print(f"处理失败: {results['failed_moves']} 个")
            print(f"跳过文件: {results['skipped_files']} 个")
            duration = (results['end_time'] - results['start_time']).total_seconds()
            print(f"总耗时: {duration:.1f} 秒")
            print("=" * 50)
            
            # 生成AI结果JSON文件
            try:
                ai_results = []
                for ai_response in results['ai_responses']:
                    # 获取对应的详细分析结果
                    file_name = ai_response['file_name']
                    file_path = next((f['path'] for f in files if Path(f['path']).name == file_name), None)
                    
                    if file_path:
                        # 重新分析文件以获取完整信息
                        analysis_result = self.analyze_and_classify_file(str(file_path), target_base_dir)
                        
                        ai_result = {
                            'file_name': file_name,
                            'file_path': str(file_path),
                            'extracted_content': analysis_result.get('extracted_content', '')[:200] + "..." if len(analysis_result.get('extracted_content', '')) > 200 else analysis_result.get('extracted_content', ''),
                            'content_summary': analysis_result.get('content_summary', ''),
                            'recommended_folder': analysis_result.get('recommended_folder', ''),
                            'match_reason': analysis_result.get('match_reason', ''),
                            'success': analysis_result.get('success', False),
                            'timing_info': analysis_result.get('timing_info', {})
                        }
                        ai_results.append(ai_result)
                
                # 保存AI结果到JSON文件
                ai_result_file = 'ai_organize_result.json'
                with open(ai_result_file, 'w', encoding='utf-8') as f:
                    json.dump(ai_results, f, ensure_ascii=False, indent=2)
                logging.info(f"AI分析结果已保存到: {ai_result_file}")
                results['ai_result_file'] = ai_result_file
                
            except Exception as e:
                logging.warning(f"生成AI结果文件失败: {e}")
            
            if self.enable_transfer_log and self.transfer_log_manager and not dry_run:
                try:
                    session_summary = self.transfer_log_manager.end_transfer_session()
                    logging.info(f"转移日志会话结束: {session_summary}")
                except Exception as e:
                    logging.warning(f"结束转移日志会话失败: {e}")
            
            logging.info(f"安全文件整理完成: 成功 {results['successful_moves']}, 失败 {results['failed_moves']}, 跳过 {results['skipped_files']}")
            return results
        except Exception as e:
            raise FileOrganizerError(f"批量整理文件失败: {e}")
    def get_transfer_logs(self) -> List[str]:
        if not self.enable_transfer_log or not self.transfer_log_manager:
            raise FileOrganizerError("转移日志功能未启用")
        return self.transfer_log_manager.get_transfer_logs()
    def get_transfer_log_summary(self, log_file_path: str) -> Dict:
        if not self.enable_transfer_log or not self.transfer_log_manager:
            raise FileOrganizerError("转移日志功能未启用")
        return self.transfer_log_manager.get_session_summary(log_file_path)
    def restore_files_from_log(self, log_file_path: str, operation_ids: Optional[List[int]] = None, dry_run: bool = True) -> Dict:
        if not self.enable_transfer_log or not self.transfer_log_manager:
            raise FileOrganizerError("转移日志功能未启用")
        try:
            restore_results = self.transfer_log_manager.restore_from_log(
                log_file_path=log_file_path,
                operation_ids=operation_ids if operation_ids is not None else [],
                dry_run=dry_run
            )
            logging.info(f"文件恢复完成: 成功 {restore_results['successful_restores']}, 失败 {restore_results['failed_restores']}, 跳过 {restore_results['skipped_operations']}")
            return restore_results
        except Exception as e:
            raise FileOrganizerError(f"文件恢复失败: {e}")
    def cleanup_old_transfer_logs(self, days_to_keep: int = 30) -> int:
        if not self.enable_transfer_log or not self.transfer_log_manager:
            raise FileOrganizerError("转移日志功能未启用")
        return self.transfer_log_manager.cleanup_old_logs(days_to_keep)
    def get_file_summary(self, file_path: str, max_length: int = 50, max_pages: int = 2, max_seconds: int = 10) -> str:
        """
        自动适配 txt/pdf/docx 格式，返回前max_length字摘要，PDF/Word只取前max_pages页，单文件处理超时max_seconds秒。
        """
        ext = Path(file_path).suffix.lower()
        start_time = time.time()
        try:
            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(max_length)
            elif ext == '.pdf':
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ''
                    for i, page in enumerate(reader.pages):
                        if i >= max_pages or (time.time() - start_time) > max_seconds:
                            break
                        page_text = page.extract_text() or ''
                        text += page_text
                        if len(text) >= max_length:
                            break
                    if (time.time() - start_time) > max_seconds:
                        return '提取超时，已跳过'
                    return text[:max_length] if text else '未能提取正文'
            elif ext == '.docx':
                doc = docx.Document(file_path)
                text = ''
                for i, para in enumerate(doc.paragraphs):
                    if (time.time() - start_time) > max_seconds:
                        break
                    text += para.text
                    if len(text) >= max_length:
                        break
                if (time.time() - start_time) > max_seconds:
                    return '提取超时，已跳过'
                return text[:max_length] if text else '未能提取正文'
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(max_length)
        except Exception as e:
            if (time.time() - start_time) > max_seconds:
                return '提取超时，已跳过'
            return f'摘要获取失败: {e}'