#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文件分类器 - 全新实现
按照用户提供的业务逻辑：递归逐层匹配，每次只传递一层目录
"""
import os
import sys
import time
import json
import logging
import re
import signal
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from ai_client_manager import chat_with_ai

class TimeoutError(Exception):
    """超时异常"""
    pass

def timeout_handler(signum, frame):
    """超时信号处理器"""
    raise TimeoutError("操作超时")

class SmartFileClassifier:
    """智能文件分类器"""
    
    def __init__(self, content_extraction_length: int = 2000, summary_length: int = 150, timeout_seconds: int = 180):
        """
        初始化智能文件分类器
        
        Args:
            content_extraction_length: 内容提取长度（从GUI获取）
            summary_length: 摘要长度（从GUI获取）
            timeout_seconds: 单个文件处理超时时间（秒），默认3分钟
        """
        self.content_extraction_length = content_extraction_length
        self.summary_length = summary_length
        self.timeout_seconds = timeout_seconds
        
        # 文件缓存
        self.file_cache = {}  # 缓存文件信息和元数据
        self.level_tags = {}  # 缓存各级标签
        
        # 设置日志
        self.setup_logging()
        
        # 加载分类规则
        self.classification_rules = self.load_classification_rules()
        
        logging.info("智能文件分类器初始化完成")
    
    def setup_logging(self):
        """设置日志"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f"smart_classifier_{timestamp}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def load_classification_rules(self) -> Dict[str, str]:
        """加载分类规则"""
        try:
            if os.path.exists('classification_rules.json'):
                with open('classification_rules.json', 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                logging.info(f"成功加载分类规则，共 {len(rules)} 条规则")
                return rules
            else:
                logging.warning("分类规则文件不存在，使用默认规则")
                return {}
        except Exception as e:
            logging.error(f"加载分类规则失败: {e}")
            return {}
    
    def extract_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取文件元数据"""
        try:
            file_path_obj = Path(file_path)
            stat = file_path_obj.stat()
            
            # 获取文件扩展名
            file_extension = file_path_obj.suffix.lower()
            
            # 获取文件大小（字节）
            file_size = stat.st_size
            
            # 获取创建时间和修改时间
            created_time = datetime.fromtimestamp(stat.st_ctime).isoformat()
            modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            return {
                'file_name': file_path_obj.name,
                'file_extension': file_extension,
                'file_size': file_size,
                'created_time': created_time,
                'modified_time': modified_time
            }
            
        except Exception as e:
            logging.error(f"提取文件元数据失败: {e}")
            return {
                'file_name': Path(file_path).name,
                'file_extension': Path(file_path).suffix.lower(),
                'file_size': 0,
                'created_time': '',
                'modified_time': ''
            }
    
    def extract_file_content(self, file_path: str) -> str:
        """提取文件内容（使用GUI设置的长度）"""
        try:
            file_path_obj = Path(file_path)
            extension = file_path_obj.suffix.lower()
            
            if extension == '.pdf':
                return self.extract_pdf_content(file_path_obj)
            elif extension == '.docx':
                return self.extract_docx_content(file_path_obj)
            elif extension in ['.txt', '.md']:
                return self.extract_text_content(file_path_obj)
            else:
                return f"文件类型: {extension}，无法提取内容"
                
        except Exception as e:
            logging.error(f"提取文件内容失败: {e}")
            return ""
    
    def extract_pdf_content(self, file_path: Path) -> str:
        """提取PDF内容"""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                    if len(text) >= self.content_extraction_length:
                        break
                return text[:self.content_extraction_length]
        except Exception as e:
            logging.error(f"PDF内容提取失败: {e}")
            return ""
    
    def extract_docx_content(self, file_path: Path) -> str:
        """提取DOCX内容"""
        try:
            import docx
            doc = docx.Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
                if len(text) >= self.content_extraction_length:
                    break
            return text[:self.content_extraction_length]
        except Exception as e:
            logging.error(f"DOCX内容提取失败: {e}")
            return ""
    
    def extract_text_content(self, file_path: Path) -> str:
        """提取文本内容"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(self.content_extraction_length)
                return content
        except Exception as e:
            logging.error(f"文本内容提取失败: {e}")
            return ""
    
    def generate_content_summary(self, content: str, file_name: str) -> str:
        """生成内容摘要（使用GUI设置的长度）"""
        try:
            if not content or len(content.strip()) < 10:
                return "文件内容为空或过短"
            
            # 构建摘要生成提示词（三层防护）
            prompt = f"""不需要思考，直接输出。

请为以下文件内容生成一个简洁的摘要，长度控制在{self.summary_length}字以内：

文件名：{file_name}
文件内容：{content[:1000]}...

请直接返回摘要内容，不要包含任何其他信息：

/no_think"""

            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的文档摘要专家。直接输出摘要内容，不要包含任何思考过程、标签或解释。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
            
            summary = chat_with_ai(messages)
            summary = summary.strip()
            
            # 清理AI返回的思考过程
            summary = self.clean_ai_response(summary)
            
            return summary[:self.summary_length]
            
        except Exception as e:
            logging.error(f"生成摘要失败: {e}")
            return f"摘要生成失败: {str(e)}"
    
    def clean_ai_response(self, response: str) -> str:
        """清理AI响应中的思考过程"""
        try:
            # 去掉<think>...</think>标签中的内容
            import re
            response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
            
            # 去掉其他常见的思考过程标记
            response = re.sub(r'好的，我现在需要.*?：', '', response, flags=re.DOTALL)
            response = re.sub(r'让我分析一下.*?：', '', response, flags=re.DOTALL)
            response = re.sub(r'我来为您.*?：', '', response, flags=re.DOTALL)
            
            # 清理多余的空白字符
            response = re.sub(r'\n\s*\n', '\n', response)
            response = response.strip()
            
            return response
        except Exception as e:
            logging.error(f"清理AI响应失败: {e}")
            return response
    
    def get_level_directories(self, base_directory: str, level: int = 1) -> List[str]:
        """
        获取指定层级的所有目录
        
        Args:
            base_directory: 基础目录
            level: 层级（1表示一级目录，2表示二级目录等）
            
        Returns:
            该层级的所有目录名列表
        """
        try:
            if level == 1:
                # 使用os.listdir获取一级目录，更简单高效
                dirs = [name for name in os.listdir(base_directory) 
                       if os.path.isdir(os.path.join(base_directory, name))]
                return dirs
            else:
                # 对于多级目录，使用pathlib
                base_path = Path(base_directory)
                if not base_path.exists():
                    return []
                
                directories = []
                for item in base_path.rglob('*'):
                    if item.is_dir():
                        # 计算相对路径的层级
                        relative_path = item.relative_to(base_path)
                        path_parts = relative_path.parts
                        if len(path_parts) == level:
                            directories.append(item.name)
                
                return directories
                
        except Exception as e:
            logging.error(f"获取{level}级目录失败: {e}")
            return []
    
    def match_level_directory(self, file_info: Dict[str, Any], content: str, summary: str, 
                             base_directory: str, current_path: str, level: int) -> Tuple[str, str]:
        """
        匹配指定层级的目录
        
        Args:
            file_info: 文件信息字典
            content: 文件内容
            summary: 文件摘要
            base_directory: 基础目录
            current_path: 当前已匹配的路径
            level: 当前匹配的层级
            
        Returns:
            (匹配的目录名, 匹配理由)
        """
        try:
            # 获取当前层级的所有目录
            level_dirs = self.get_level_directories(base_directory, level)
            if not level_dirs:
                return "", "该层级没有子目录"
            
            file_name = file_info['file_name']
            file_extension = file_info['file_extension']
            
            # 第一步：优先检查文件名中的年份匹配
            time_match_dir = self.find_best_time_match(file_name, level_dirs)
            if time_match_dir:
                match_reason = f"文件名年份匹配: 文件名包含年份，匹配到 {time_match_dir}"
                return time_match_dir, match_reason
            
            # 第二步：检查目录名是否直接包含在文件名中
            for dir_name in level_dirs:
                if dir_name.lower() in file_name.lower():
                    match_reason = f"文件名包含: 文件名包含目录名 {dir_name}"
                    return dir_name, match_reason
            
            # 第三步：使用AI进行智能匹配
            # 获取用户自定义分类规则
            custom_rules = self.get_custom_rules_for_prompt(level_dirs)
            
            # 构建简化的匹配提示词（三层防护）
            prompt = f"""不需要思考，直接输出。

你是一个专业的文件分类专家。请根据文件信息在当前层级目录中选择最匹配的一个。

文件信息：
- 文件名：{file_name}
- 文件扩展名：{file_extension}
- 内容摘要：{summary[:150] if summary else '无摘要'}

当前层级可选目录（必须严格从以下列表中选择一个，不要添加任何序号、标点或额外字符）：
{chr(10).join(level_dirs)}

{custom_rules}

匹配优先级：
1. 最高优先级：目录名是时间命名（如年份、月份），而文件名中包含对应时间
2. 高优先级：目录名直接包含在文件名中
3. 中优先级：目录名与文件内容主题高度相关（请仔细阅读上面的分类规则说明）
4. 低优先级：根据文件类型和扩展名匹配

请只返回一个最匹配的目录名，不要包含任何其他内容：

/no_think"""

            # 调用AI进行匹配
            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的文件分类专家。直接输出目录名，不要包含任何思考过程、标签、序号或解释。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
            
            result = chat_with_ai(messages)
            result = self.clean_ai_response(result)
            
            # 清理AI返回的结果，去除序号和多余字符
            result = self.clean_directory_name(result, level_dirs)
            
            # 验证结果是否在可选目录中
            if result in level_dirs:
                # 确定匹配理由
                match_reason = self.determine_match_reason(file_name, result, summary)
                return result, match_reason
            else:
                # 如果AI返回的结果不在列表中，尝试模糊匹配
                for dir_name in level_dirs:
                    if self.fuzzy_match(file_name, dir_name, summary):
                        match_reason = f"模糊匹配到: {dir_name}"
                        return dir_name, match_reason
                
                # 如果都没有匹配到，直接失败
                logging.warning(f"AI返回的目录 '{result}' 不在可选目录列表中，匹配失败")
                return "", f"匹配失败: AI返回的目录不在可选列表中"
                
        except Exception as e:
            logging.error(f"匹配{level}级目录失败: {e}")
            return "", f"匹配失败: {str(e)}"
    
    def get_custom_rules_for_prompt(self, level_dirs: List[str]) -> str:
        """获取自定义分类规则"""
        if not self.classification_rules:
            return ""
        
        relevant_rules = []
        for dir_name in level_dirs:
            if dir_name in self.classification_rules:
                relevant_rules.append(f"{dir_name}: {self.classification_rules[dir_name]}")
        
        if relevant_rules:
            return f"\n用户自定义分类规则：\n{chr(10).join(relevant_rules)}"
        else:
            return ""
    
    def determine_match_reason(self, file_name: str, dir_name: str, summary: str) -> str:
        """确定匹配理由"""
        if self.is_time_match(file_name, dir_name):
            return f"时间匹配: 文件名包含时间信息，匹配到 {dir_name}"
        elif dir_name.lower() in file_name.lower():
            return f"文件名包含: 文件名包含目录名 {dir_name}"
        else:
            return f"AI智能分类: 根据文件内容匹配到 {dir_name}"
    
    def is_time_match(self, file_name: str, dir_name: str) -> bool:
        """检查是否为时间匹配"""
        try:
            # 从目录名中提取年份
            year_match = re.search(r'(\d{4})', dir_name)
            if not year_match:
                return False
            
            year = year_match.group(1)
            return year in file_name
        except:
            return False
    
    def extract_year_from_filename(self, file_name: str) -> Optional[int]:
        """从文件名中提取年份"""
        try:
            # 提取4位数字年份
            year_match = re.search(r'(\d{4})', file_name)
            if year_match:
                year = int(year_match.group(1))
                # 合理的年份范围
                if 1900 <= year <= 2030:
                    return year
            return None
        except:
            return None
    
    def find_best_time_match(self, file_name: str, level_dirs: List[str]) -> Optional[str]:
        """找到最佳的时间匹配目录"""
        try:
            file_year = self.extract_year_from_filename(file_name)
            if not file_year:
                return None
            
            # 寻找包含该年份的目录
            for dir_name in level_dirs:
                year_match = re.search(r'(\d{4})', dir_name)
                if year_match:
                    dir_year = int(year_match.group(1))
                    if dir_year == file_year:
                        return dir_name
            
            return None
        except:
            return None
    
    def fuzzy_match(self, file_name: str, dir_name: str, summary: str) -> bool:
        """模糊匹配"""
        try:
            # 简单的关键词匹配
            keywords = dir_name.lower().split()
            file_text = (file_name + " " + summary).lower()
            
            for keyword in keywords:
                if len(keyword) > 2 and keyword in file_text:
                    return True
            
            return False
        except:
            return False
    
    def clean_directory_name(self, ai_result: str, valid_dirs: List[str]) -> str:
        """清理AI返回的目录名，去除序号和多余字符"""
        try:
            if not ai_result:
                return ""
            
            # 去除常见的序号格式
            cleaned = ai_result.strip()
            
            # 去除各种序号格式
            patterns = [
                r'^\d+\.\s*',      # "1. "
                r'^\d+\s*',        # "1 "
                r'^\d+、\s*',      # "1、 "
                r'^\d+）\s*',      # "1） "
                r'^\d+\)\s*',      # "1) "
                r'^\d+\.\s*',      # "1. "
                r'^\d+\s*',        # "1 "
            ]
            
            for pattern in patterns:
                cleaned = re.sub(pattern, '', cleaned)
            
            # 去除首尾空白字符
            cleaned = cleaned.strip()
            
            # 如果清理后的结果在有效目录列表中，返回清理后的结果
            if cleaned in valid_dirs:
                return cleaned
            
            # 如果不在列表中，尝试模糊匹配
            for valid_dir in valid_dirs:
                if cleaned.lower() == valid_dir.lower():
                    return valid_dir
                if valid_dir.lower() in cleaned.lower():
                    return valid_dir
                # 检查是否包含有效目录名（去除序号后）
                if cleaned.lower().replace(' ', '') == valid_dir.lower().replace(' ', ''):
                    return valid_dir
            
            # 如果都不匹配，返回原始结果
            return ai_result.strip()
            
        except Exception as e:
            logging.error(f"清理目录名失败: {e}")
            return ai_result.strip()
    
    def recommend_target_folder_recursive(self, file_path: str, content: str, summary: str, 
                                         target_directory: str) -> Tuple[str, List[str], str]:
        """
        递归逐层匹配推荐目标文件夹
        
        Args:
            file_path: 文件路径
            content: 文件内容
            summary: 文件摘要
            target_directory: 目标目录
            
        Returns:
            (推荐路径, 各级标签, 匹配理由)
        """
        try:
            file_info = self.extract_file_metadata(file_path)
            self.file_cache[file_path] = file_info
            
            current_path = ""
            level_tags = []
            match_reasons = []
            current_base_dir = target_directory
            
            level = 1
            max_levels = 10  # 防止无限递归
            
            while level <= max_levels:
                logging.info(f"开始匹配第{level}级目录，当前路径: {current_path}")
                
                # 匹配当前层级目录
                matched_dir, match_reason = self.match_level_directory(
                    file_info, content, summary, current_base_dir, current_path, level
                )
                
                if not matched_dir:
                    logging.info(f"第{level}级目录匹配失败，停止递归")
                    # 如果没有匹配理由，设置默认理由
                    if not match_reason:
                        match_reason = f"第{level}级目录匹配失败：无法找到合适的分类目录"
                    break
                
                # 更新路径和标签
                if current_path:
                    current_path = f"{current_path}\\{matched_dir}"
                else:
                    current_path = matched_dir
                
                level_tags.append(matched_dir)
                match_reasons.append(f"第{level}级: {match_reason}")
                
                # 检查下一级是否有子目录
                next_base_dir = os.path.join(current_base_dir, matched_dir)
                # 统一路径格式，避免\和/混用
                next_base_dir = os.path.normpath(next_base_dir)
                next_level_dirs = self.get_level_directories(next_base_dir, 1)
                
                if not next_level_dirs:
                    logging.info(f"第{level}级目录 {matched_dir} 下没有子目录，停止递归")
                    break
                
                current_base_dir = next_base_dir
                level += 1
            
            # 缓存标签
            self.level_tags[file_path] = level_tags
            
            # 组合匹配理由
            combined_reason = "; ".join(match_reasons)
            
            logging.info(f"递归匹配完成: {current_path}, 标签: {level_tags}")
            
            return current_path, level_tags, combined_reason
            
        except Exception as e:
            logging.error(f"递归匹配失败: {e}")
            return "", [], f"递归匹配失败: {str(e)}"
    
    def classify_file(self, file_path: str, target_directory: str) -> Dict[str, Any]:
        """
        分类单个文件（带超时保护）
        
        Args:
            file_path: 文件路径
            target_directory: 目标目录
            
        Returns:
            分类结果字典
        """
        start_time = time.time()
        timing_info = {}
        
        try:
            file_name = Path(file_path).name
            logging.info(f"开始分类文件: {file_name}（超时限制: {self.timeout_seconds}秒）")
            
            # 使用超时机制包装整个分类过程
            def classify_with_timeout():
                # 第一步：提取文件元数据
                metadata_start = time.time()
                file_metadata = self.extract_file_metadata(file_path)
                metadata_time = round(time.time() - metadata_start, 3)
                timing_info['metadata_extraction_time'] = metadata_time
                logging.info(f"文件元数据提取完成，耗时: {metadata_time}秒")
                
                # 第二步：提取文件内容（使用GUI设置的长度）
                extract_start = time.time()
                content = self.extract_file_content(file_path)
                extract_time = round(time.time() - extract_start, 3)
                timing_info['content_extraction_time'] = extract_time
                logging.info(f"文件内容提取完成，长度: {len(content)} 字符，耗时: {extract_time}秒")
                
                # 第三步：生成摘要（使用GUI设置的长度）
                summary_start = time.time()
                summary = self.generate_content_summary(content, file_name)
                summary_time = round(time.time() - summary_start, 3)
                timing_info['summary_generation_time'] = summary_time
                logging.info(f"内容摘要生成完成，长度: {len(summary)} 字符，耗时: {summary_time}秒")
                
                # 第四步：递归逐层匹配推荐目录
                recommend_start = time.time()
                recommended_folder, level_tags, match_reason = self.recommend_target_folder_recursive(
                    file_path, content, summary, target_directory
                )
                recommend_time = round(time.time() - recommend_start, 3)
                timing_info['folder_recommendation_time'] = recommend_time
                
                return file_metadata, content, summary, recommended_folder, level_tags, match_reason
            
            # 执行带超时的分类
            file_metadata, content, summary, recommended_folder, level_tags, match_reason = self.run_with_timeout(classify_with_timeout)
            
            total_time = round(time.time() - start_time, 3)
            timing_info['total_processing_time'] = total_time
            
            if recommended_folder:
                logging.info(f"文件分类完成: {file_name} -> {recommended_folder}，总耗时: {total_time}秒")
                logging.info(f"摘要: {summary}")
                logging.info(f"推荐理由: {match_reason}")
                logging.info(f"各级标签: {level_tags}")
            else:
                # 如果匹配失败，设置默认的失败理由
                if not match_reason:
                    match_reason = "分类失败：无法匹配到合适的目录"
                logging.warning(f"文件分类失败: {file_name}，总耗时: {total_time}秒")
                logging.warning(f"失败理由: {match_reason}")
            
            result = {
                'file_path': file_path,
                'file_name': file_name,
                'file_metadata': file_metadata,
                'extracted_content': content,
                'content_summary': summary,
                'recommended_folder': recommended_folder,
                'level_tags': level_tags,
                'match_reason': match_reason,  # 使用可能被修改的match_reason
                'success': bool(recommended_folder),
                'timing_info': timing_info
            }
            
            return result
            
        except TimeoutError as e:
            total_time = round(time.time() - start_time, 3)
            timing_info['total_processing_time'] = total_time
            logging.error(f"文件分类超时: {file_name}，总耗时: {total_time}秒，超时限制: {self.timeout_seconds}秒")
            return {
                'file_path': file_path,
                'file_name': Path(file_path).name,
                'file_metadata': {},
                'extracted_content': '',
                'content_summary': '',
                'recommended_folder': None,
                'level_tags': [],
                'match_reason': f"分类超时：处理时间超过{self.timeout_seconds}秒",
                'success': False,
                'error': str(e),
                'timing_info': timing_info
            }
        except Exception as e:
            total_time = round(time.time() - start_time, 3)
            timing_info['total_processing_time'] = total_time
            logging.error(f"文件分类失败: {e}，总耗时: {total_time}秒")
            return {
                'file_path': file_path,
                'file_name': Path(file_path).name,
                'file_metadata': {},
                'extracted_content': '',
                'content_summary': '',
                'recommended_folder': None,
                'level_tags': [],
                'match_reason': f"分类失败: {str(e)}",
                'success': False,
                'error': str(e),
                'timing_info': timing_info
            }
    
    def clear_file_cache(self, file_path: str) -> None:
        """清除文件缓存"""
        if file_path in self.file_cache:
            del self.file_cache[file_path]
        if file_path in self.level_tags:
            del self.level_tags[file_path]
    
    def append_result_to_file(self, ai_result_file: str, result: dict, target_directory: str = "") -> None:
        """将AI结果追加到JSON文件"""
        try:
            # 构建结果条目
            entry = {
                "处理时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "文件名": result['file_name'],
                "文件摘要": result['content_summary'],
                "最匹配的目标目录": result['recommended_folder'] if result['success'] else "分类失败",
                "处理耗时": result['timing_info'].get('total_processing_time', 0),
                "最终目标路径": os.path.join(target_directory, result['recommended_folder'], result['file_name']) if result['success'] and result['recommended_folder'] else "",
                "操作类型": "文件迁移",
                "处理状态": "迁移成功" if result['success'] else "迁移失败",
                "标签": {
                    f"{i+1}级标签": tag for i, tag in enumerate(result['level_tags'])
                },
                "文件元数据": {
                    "file_name": result['file_metadata']['file_name'],
                    "file_extension": result['file_metadata']['file_extension'],
                    "file_size": result['file_metadata']['file_size'],
                    "created_time": result['file_metadata']['created_time'],
                    "modified_time": result['file_metadata']['modified_time']
                }
            }
            
            # 读取现有文件
            existing_data = []
            if os.path.exists(ai_result_file):
                try:
                    with open(ai_result_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_data = []
            
            # 添加新条目
            existing_data.append(entry)
            
            # 写入文件
            with open(ai_result_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"结果已写入: {ai_result_file}")
            
        except Exception as e:
            logging.error(f"写入结果文件失败: {e}") 

    def run_with_timeout(self, func, *args, **kwargs):
        """
        在超时限制下运行函数
        
        Args:
            func: 要执行的函数
            *args, **kwargs: 函数参数
            
        Returns:
            函数执行结果
            
        Raises:
            TimeoutError: 如果函数执行超时
        """
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.timeout_seconds)
        
        if thread.is_alive():
            logging.warning(f"函数执行超时（{self.timeout_seconds}秒）")
            raise TimeoutError(f"操作超时（{self.timeout_seconds}秒）")
        
        if exception[0]:
            raise exception[0]
        
        return result[0] 