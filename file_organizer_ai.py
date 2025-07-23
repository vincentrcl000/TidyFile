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
from classification_rules_manager import ClassificationRulesManager
import PyPDF2
import docx
import time
import requests

class FileOrganizerError(Exception):
    pass

class OllamaClient:
    def __init__(self, model_name: str = None, host: str = None):
        self.model_name = model_name
        # 优先LM Studio，其次局域网Ollama，最后本地Ollama
        self.hosts_to_try = [
            "http://10.64.21.220:1234/v1",  # LM Studio
            "http://10.64.21.220:11434",    # 局域网Ollama
            "http://localhost:11434"        # 本地Ollama
        ] if host is None else [host]
        self.client = None
        self.available_models = []
        self._try_connect_and_select_model()

    def _try_connect_and_select_model(self):
        last_error = None
        for host in self.hosts_to_try:
            try:
                self.host = host
                if "1234/v1" in host:  # LM Studio API
                    self.client = self._create_lmstudio_client(host)
                else:  # Ollama API
                    self.client = ollama.Client(host=host)
                self._validate_connection()
                logging.info(f"成功连接到AI服务: {host}")
                return
            except Exception as e:
                last_error = e
                logging.warning(f"连接AI服务失败: {host}，错误: {e}")
                continue
        raise FileOrganizerError(f"所有AI服务连接失败，最后错误: {last_error}")

    def _create_lmstudio_client(self, host: str):
        """创建LM Studio客户端（兼容Ollama API）"""
        class LMStudioClient:
            def __init__(self, host):
                self.host = host
                self.base_url = host
            def list(self):
                try:
                    response = requests.get(f"{self.base_url}/models", timeout=10)
                    response.raise_for_status()
                    models_data = response.json()
                    # 转换为Ollama格式，只返回loaded状态的模型
                    models = []
                    for model in models_data.get('data', []):
                        # 检查模型状态，只返回loaded状态的模型
                        if model.get('status') == 'loaded':
                            models.append({'name': model.get('id', '')})
                    return {'models': models}
                except Exception as e:
                    raise Exception(f"LM Studio API调用失败: {e}")
            def chat(self, **kwargs):
                try:
                    messages = kwargs.get('messages', [])
                    model = kwargs.get('model', '')
                    # 转换为LM Studio格式
                    lmstudio_messages = []
                    for msg in messages:
                        lmstudio_messages.append({
                            'role': msg.get('role', 'user'),
                            'content': msg.get('content', '')
                        })
                    payload = {
                        'model': model,
                        'messages': lmstudio_messages,
                        'stream': False
                    }
                    response = requests.post(f"{self.base_url}/chat/completions", 
                                           json=payload, timeout=60)
                    
                    # 检查HTTP状态码
                    if response.status_code != 200:
                        error_msg = f"LM Studio API返回错误状态码: {response.status_code}"
                        try:
                            error_data = response.json()
                            if 'error' in error_data:
                                error_msg += f", 错误信息: {error_data['error']}"
                        except:
                            error_msg += f", 响应内容: {response.text[:200]}"
                        raise Exception(error_msg)
                    
                    result = response.json()
                    
                    # 检查响应格式
                    if 'choices' not in result or not result['choices']:
                        raise Exception(f"LM Studio响应格式错误: {result}")
                    
                    choice = result['choices'][0]
                    if 'message' not in choice or 'content' not in choice['message']:
                        raise Exception(f"LM Studio响应缺少message或content: {choice}")
                    
                    # 转换为Ollama格式
                    return {
                        'message': {
                            'content': choice['message']['content']
                        }
                    }
                except Exception as e:
                    raise Exception(f"LM Studio chat调用失败: {e}")
        return LMStudioClient(host)

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
                        model_str = str(model)
                        if "model='" in model_str:
                            import re
                            match = re.search(r"model='([^']+)'", model_str)
                            if match:
                                self.available_models.append(match.group(1))
                            else:
                                self.available_models.append(model_str)
                        else:
                            self.available_models.append(model_str)
            # 优先选择qwen/qwen3-8b模型（LM Studio），其次qwen3:8b（Ollama）
            preferred_models = []
            qwen_qwen3_8b = [m for m in self.available_models if 'qwen/qwen3-8b' in m.lower()]
            if qwen_qwen3_8b:
                preferred_models.extend(qwen_qwen3_8b)
                logging.info(f"优先选择LM Studio qwen/qwen3-8b模型: {qwen_qwen3_8b}")
            else:
                qwen3_8b = [m for m in self.available_models if 'qwen3:8b' in m.lower()]
                if qwen3_8b:
                    preferred_models.extend(qwen3_8b)
                    logging.info(f"优先选择Ollama qwen3:8b模型: {qwen3_8b}")
                else:
                    # 其次qwen3系列
                    qwen3_models = [m for m in self.available_models if 'qwen3' in m.lower()]
                    if qwen3_models:
                        preferred_models.extend(qwen3_models)
                        logging.info(f"找到qwen3系列模型: {qwen3_models}")
                    # 其次deepseek系列
                    deepseek_models = [m for m in self.available_models if 'deepseek' in m.lower()]
                    if deepseek_models:
                        preferred_models.extend(deepseek_models)
                        logging.info(f"找到deepseek系列模型: {deepseek_models}")
                    # 其它
                    other_models = [m for m in self.available_models if 'qwen3' not in m.lower() and 'deepseek' not in m.lower()]
                    preferred_models.extend(other_models)
            if preferred_models:
                self.model_name = preferred_models[0]
                logging.info(f"自动选择模型: {self.model_name}")
            else:
                self.model_name = self.available_models[0]
                logging.info(f"使用默认模型: {self.model_name}")
            logging.info(f"可用模型列表: {self.available_models}")
        except Exception as e:
            raise FileOrganizerError(f"连接 AI 服务失败: {e}")
    
    def chat_with_retry(self, messages: List[Dict], max_retries: Optional[int] = None) -> str:
        if max_retries is None:
            max_retries = len(self.available_models)
        last_error = None
        
        # 首先尝试当前已连接的host
        models_to_try = [self.model_name] + [m for m in self.available_models if m != self.model_name]
        
        logging.info(f"开始尝试当前host的模型，可用模型: {self.available_models}")
        logging.info(f"将尝试的模型顺序: {models_to_try[:max_retries]}")
        
        for attempt, model_name in enumerate(models_to_try[:max_retries]):
            try:
                if not isinstance(model_name, str) or not model_name:
                    logging.warning(f"跳过无效模型名: {model_name}")
                    continue
                
                # 使用已初始化的客户端，而不是重新创建
                if not self.client:
                    raise FileOrganizerError("客户端未初始化")
                
                logging.info(f"尝试使用模型: {model_name} (第{attempt + 1}次尝试)")
                
                # 根据客户端类型使用不同的调用方式
                if hasattr(self.client, 'chat'):
                    # 使用自定义客户端（如LMStudioClient）
                    chat_params = {
                        'model': model_name,
                        'messages': messages
                    }
                    response = self.client.chat(**chat_params)
                else:
                    # 使用Ollama客户端
                    chat_params = {
                        'model': model_name,
                        'messages': messages,
                        'options': {'enable_thinking': False}
                    }
                    response = self.client.chat(**chat_params)
                
                # 验证响应格式
                if not response or 'message' not in response or 'content' not in response['message']:
                    raise FileOrganizerError(f"模型 {model_name} 返回无效响应格式: {response}")
                
                content = response['message']['content'].strip()
                if not content:
                    raise FileOrganizerError(f"模型 {model_name} 返回空内容")
                
                if model_name != self.model_name:
                    logging.info(f"模型切换成功: {self.model_name} -> {model_name}")
                    self.model_name = model_name
                
                logging.info(f"模型 {model_name} 响应成功")
                return content
                
            except Exception as e:
                last_error = e
                logging.warning(f"模型 {model_name} 响应失败: {e}")
                if attempt < max_retries - 1:
                    logging.info(f"准备尝试下一个模型...")
                    continue
        
        # 当前host的所有模型都失败了，尝试其他host
        logging.warning(f"当前host {self.host} 的所有模型都失败，尝试其他host...")
        
        # 尝试其他host
        for host in self.hosts_to_try:
            if host == self.host:  # 跳过当前已失败的host
                continue
                
            try:
                logging.info(f"尝试连接到host: {host}")
                if "1234/v1" in host:  # LM Studio API
                    client = self._create_lmstudio_client(host)
                else:  # Ollama API
                    client = ollama.Client(host=host)
                
                # 获取该host的可用模型
                models_response = client.list()
                if hasattr(models_response, 'models'):
                    models_list = models_response.models
                elif isinstance(models_response, dict) and 'models' in models_response:
                    models_list = models_response['models']
                else:
                    models_list = models_response if isinstance(models_response, list) else []
                
                available_models = []
                for model in models_list:
                    if isinstance(model, dict):
                        if 'name' in model:
                            model_name = model['name']
                            if isinstance(model_name, str):
                                available_models.append(model_name)
                            else:
                                available_models.append(str(model_name))
                        elif 'model' in model:
                            model_name = model['model']
                            if isinstance(model_name, str):
                                available_models.append(model_name)
                            else:
                                available_models.append(str(model_name))
                    elif isinstance(model, str):
                        available_models.append(model)
                    else:
                        model_name = None
                        if hasattr(model, 'model'):
                            model_name = getattr(model, 'model')
                        elif hasattr(model, 'name'):
                            model_name = getattr(model, 'name')
                        if model_name:
                            if isinstance(model_name, str):
                                available_models.append(model_name)
                            else:
                                available_models.append(str(model_name))
                
                if not available_models:
                    logging.warning(f"host {host} 没有可用模型")
                    continue
                
                # 优先模型顺序
                models_to_try = []
                qwen3_models = [m for m in available_models if 'qwen3' in m.lower()]
                if qwen3_models:
                    models_to_try.extend(qwen3_models)
                deepseek_models = [m for m in available_models if 'deepseek' in m.lower()]
                if deepseek_models:
                    models_to_try.extend(deepseek_models)
                other_models = [m for m in available_models if 'qwen3' not in m.lower() and 'deepseek' not in m.lower()]
                models_to_try.extend(other_models)
                
                if not models_to_try:
                    models_to_try = available_models
                
                logging.info(f"host {host} 可用模型: {available_models}")
                logging.info(f"将尝试的模型顺序: {models_to_try}")
                
                # 尝试该host的模型
                for model_name in models_to_try:
                    try:
                        logging.info(f"尝试使用host {host} 的模型: {model_name}")
                        
                        if hasattr(client, 'chat'):
                            # 使用自定义客户端（如LMStudioClient）
                            chat_params = {
                                'model': model_name,
                                'messages': messages
                            }
                            response = client.chat(**chat_params)
                        else:
                            # 使用Ollama客户端
                            chat_params = {
                                'model': model_name,
                                'messages': messages,
                                'options': {'enable_thinking': False}
                            }
                            response = client.chat(**chat_params)
                        
                        # 验证响应格式
                        if not response or 'message' not in response or 'content' not in response['message']:
                            raise FileOrganizerError(f"模型 {model_name} 返回无效响应格式: {response}")
                        
                        content = response['message']['content'].strip()
                        if not content:
                            raise FileOrganizerError(f"模型 {model_name} 返回空内容")
                        
                        # 更新当前客户端和模型信息
                        self.client = client
                        self.host = host
                        self.model_name = model_name
                        self.available_models = available_models
                        
                        logging.info(f"成功切换到host {host}，使用模型: {model_name}")
                        return content
                        
                    except Exception as e:
                        last_error = e
                        logging.warning(f"host {host} 的模型 {model_name} 响应失败: {e}")
                        continue
                
                logging.warning(f"host {host} 的所有模型都失败")
                
            except Exception as e:
                last_error = e
                logging.warning(f"连接host {host} 失败: {e}")
                continue
        
        # 所有host和模型都失败了
        error_msg = f"所有可用host和模型都响应失败，最后错误: {last_error}"
        logging.error(error_msg)
        raise FileOrganizerError(error_msg)

class FileOrganizer:
    def __init__(self, model_name: str = None, enable_transfer_log: bool = True):
        self.model_name = model_name
        self.ollama_client = None
        self.enable_transfer_log = enable_transfer_log
        self.transfer_log_manager = None
        self.setup_logging()
        
        if self.enable_transfer_log:
            self.transfer_log_manager = TransferLogManager()
        
        # 初始化分类规则管理器
        self.classification_rules_manager = ClassificationRulesManager()
        
        # 初始化AI参数
        self.ai_parameters = {
            'similarity_threshold': 0.7,
            'max_retries': 3,
            'content_extraction_length': 3000,
            'summary_length': 200,
            'classification_prompt_template': None
        }
    def setup_logging(self) -> None:
        """设置日志配置，仅输出到控制台"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
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
        """扫描目标文件夹，返回相对路径列表（内部使用，不输出日志）"""
        try:
            target_path = Path(target_directory)
            if not target_path.exists():
                raise FileOrganizerError(f"目标目录不存在: {target_directory}")
            folders = []
            for item in target_path.rglob('*'):
                if item.is_dir() and item != target_path:  # 排除目标目录本身
                    relative_path = item.relative_to(target_path)
                    folders.append(str(relative_path))
            return folders
        except Exception as e:
            raise FileOrganizerError(f"扫描目标文件夹失败: {e}")
    def get_directory_tree_structure(self, target_directory: str) -> str:
        """生成目标目录结构，返回完整路径列表"""
        try:
            target_path = Path(target_directory)
            if not target_path.exists():
                raise FileOrganizerError(f"目标目录不存在: {target_directory}")
            
            # 直接扫描并构建目录结构
            folders = []
            for item in target_path.rglob('*'):
                if item.is_dir() and item != target_path:  # 排除目标目录本身
                    relative_path = item.relative_to(target_path)
                    folders.append(str(relative_path))
            
            # 构建清晰的路径列表，每行一个完整路径
            path_lines = []
            for i, folder_path in enumerate(folders, 1):
                path_lines.append(f"{i}. {folder_path}")
            
            tree_structure = "\n".join(path_lines)
            logging.info(f"生成目录路径结构，共 {len(path_lines)} 行")
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
            truncate_length = self.ai_parameters['content_extraction_length'] if self.ai_parameters['content_extraction_length'] < 2000 else len(extracted_content)
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
                file_path, content_for_ai, summary, target_directory
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
    
    def _generate_content_summary(self, content: str, file_name: str, summary_length: int = None) -> str:
        """
        生成文件内容摘要
        
        Args:
            content: 文件内容
            file_name: 文件名
            summary_length: 摘要长度（字数），如果为None则使用默认值
        """
        try:
            if not content or content.startswith("无法") or content.startswith("文件内容为二进制"):
                return f"无法生成摘要：{content[:50]}..."
            
            if not self.ollama_client:
                self.initialize_ollama()
            
            # 使用传入的摘要长度，如果没有则使用默认值
            target_length = summary_length if summary_length is not None else self.ai_parameters['summary_length']
            
            # 构建更明确的提示词，避免思考过程输出
            prompt = f"""请为以下文件内容生成一个{target_length}字以内的中文摘要。

文件名：{file_name}

文件内容：
{content}

要求：
1. 概括文件的主要内容和主题
2. 突出关键信息和要点
3. 语言简洁明了
4. 字数控制在{target_length}字以内
5. 直接输出摘要内容，不要包含任何思考过程或说明文字
6. 不要使用"<think>"标签或任何思考过程描述

摘要：/no_think"""

            # 在传递给大模型的完整内容最尾部添加/no_think标签
            final_prompt = prompt

            # 使用系统提示词来抑制思考过程
            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的文档摘要助手。重要：不要输出任何推理过程、思考步骤或解释。直接按要求输出结果。只输出摘要内容，不要包含任何其他信息。'
                },
                {
                    'role': 'user',
                    'content': final_prompt
                }
            ]

            summary = self.ollama_client.chat_with_retry(messages)
            
            # 清理可能的思考过程标签和内容
            summary = summary.replace('<think>', '').replace('</think>', '').strip()
            
            # 移除常见的思考过程开头
            think_prefixes = [
                '好的，', '好，', '嗯，', '我来', '我需要', '首先，', '让我', '现在我要',
                '用户希望', '用户要求', '用户让我', '根据', '基于', '考虑到', '让我先仔细看看',
                '用户给了我这个查询', '用户给了我这个任务', '用户给了一个任务',
                '首先，我得看一下', '首先，我要理解', '首先，我得仔细看看',
                '好的，用户让我', '用户让我生成', '内容来自文件', '重点包括', '首先，我需要确认'
            ]
            
            # 更激进的清理：移除所有以思考过程开头的句子
            lines = summary.split('\n')
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
                sentences = summary.split('。')
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
                summary = summary[-100:] if len(summary) > 100 else summary
            
            # 重新组合清理后的内容
            if cleaned_lines:
                summary = '。'.join(cleaned_lines)
            
            # 确保摘要长度不超过限制
            if len(summary) > target_length:
                summary = summary[:target_length-3] + "..."
            
            return summary.strip()
            
        except Exception as e:
            logging.error(f"生成摘要失败: {e}")
            return f"摘要生成失败: {str(e)}"
    
    def _clean_ai_response(self, response: str) -> str:
        """清理AI响应中的思考过程"""
        if not response:
            return response
        
        print(f"🔧 开始清理AI响应，原始长度: {len(response)}")
        print(f"🔧 原始响应: {response}")
        
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
        
        print(f"🔧 清理后行数: {len(cleaned_lines)}")
        
        # 如果清理后没有内容，尝试更简单的方法
        if not cleaned_lines:
            print(f"🔧 清理后没有内容，尝试句子分割方法")
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
            print(f"🔧 仍然没有内容，使用最后100个字符")
            # 取最后100个字符
            response = response[-100:] if len(response) > 100 else response
            print(f"🔧 截断后响应: {response}")
            return response
        
        # 重新组合清理后的内容，保持换行符以支持多行推荐路径
        if cleaned_lines:
            response = '\n'.join(cleaned_lines)
        
        print(f"🔧 最终清理结果: {response}")
        return response.strip()
    
    def _recommend_target_folder(self, file_path: str, content: str, summary: str, target_directory: str, retry_count: int = 0) -> tuple:
        """
        基于文件内容和摘要推荐最匹配的目标文件夹
        支持重试机制，当AI返回不存在的文件夹时自动重试
        """
        try:
            if not self.ollama_client:
                self.initialize_ollama()
            
            file_name = Path(file_path).name
            file_full_path = str(Path(file_path).absolute())
            
            directory_structure = self.get_directory_tree_structure(target_directory)
            
            print(f"📄 源文件完整路径: {file_full_path}")
            print(f"📋 目录结构:\n{directory_structure}")
            if retry_count > 0:
                print(f"🔄 第 {retry_count} 次重试AI分类")
            
            # 存储AI推荐的完整路径
            self.recommended_folder_path = None
            # 存储源文件完整路径
            self.source_file_path = file_full_path
            
            # 判断是否有有效的内容和摘要
            has_valid_content = content and not content.startswith("无法") and not content.startswith("文件内容为二进制")
            has_valid_summary = summary and not summary.startswith("无法") and not summary.startswith("摘要生成失败")
            
            print(f"📄 文件内容有效: {has_valid_content}")
            print(f"📝 摘要有效: {has_valid_summary}")
            if has_valid_summary:
                print(f"📝 摘要内容: {summary[:100]}...")
            
            # 获取用户自定义分类规则
            custom_rules = self.classification_rules_manager.get_rules_for_prompt(
                self.scan_target_folders(target_directory)
            )
            
            # 构建更明确的分类提示词，要求返回前三个匹配度最高的路径
            if has_valid_content and has_valid_summary:
                prompt = f"""你是一个专业的保险行业文件分类专家。请根据文件内容精确分类到最合适的目标文件夹。

文件信息：
- 文件名：{file_name}
- 内容摘要：{summary}

可选的目标文件夹路径（必须严格从以下列表中选择，不能修改路径）：
{directory_structure}

{custom_rules}

保险行业分类指导原则：
1. **人身险类**：寿险、健康险、意外险、年金险等相关文档 → 【7-4-5】人身险
2. **财产险类**：车险、家财险、责任险、工程险等相关文档 → 【7-4-6】财产险
3. **再保险类**：再保险业务、分保、风险分散等相关文档 → 【7-4-7】再保险
4. **保险资管类**：投资管理、资产管理、资金运用等相关文档 → 【7-4-8】保险资管
5. **保险中介类**：代理、经纪、公估等相关文档 → 【7-4-9】保险中介
6. **新兴业态类**：互联网保险、科技保险、创新业务等相关文档 → 【7-4-10】新兴业态
7. **监管政策类**：保监会政策、监管规定、合规要求等相关文档 → 【7-4-2】保监会
8. **公司经营类**：公司管理、经营策略、市场分析等相关文档 → 【7-4-1】综合
9. **保险公司类**：具体保险公司相关文档 → 【7-4-4】保险公司

分类要求：
1. 必须严格从上述文件夹路径列表中复制完整的路径
2. 不能修改、缩写或添加任何内容到路径
3. 不能创建或想象不存在的文件夹
4. 优先选择最具体的分类，避免选择过于宽泛的"综合"类
5. 按匹配度从高到低返回前三个路径
6. 每行一个路径，不要包含任何其他内容
7. 不要使用"<think>"标签或任何思考过程描述
8. 仔细分析文件内容主题，选择最匹配的专业分类
9. 优先参考用户自定义分类规则进行判断

输出格式（严格按此格式，每行一个完整路径）：
第一推荐：[完整路径1]
第二推荐：[完整路径2]
第三推荐：[完整路径3]

请开始推荐："""
            else:
                # 无法获取有效内容时，使用文件名进行分类，同样返回前三个推荐
                file_extension = Path(file_name).suffix.lower()
                
                prompt = f"""你是一个专业的保险行业文件分类专家。由于无法读取文件内容，请根据文件名和扩展名精确分类到最合适的目标文件夹。

文件信息：
- 文件名：{file_name}
- 文件扩展名：{file_extension}

可选的目标文件夹路径（必须严格从以下列表中选择，不能修改路径）：
{directory_structure}

{custom_rules}

保险行业分类指导原则：
1. **人身险类**：寿险、健康险、意外险、年金险等相关文档 → 【7-4-5】人身险
2. **财产险类**：车险、家财险、责任险、工程险等相关文档 → 【7-4-6】财产险
3. **再保险类**：再保险业务、分保、风险分散等相关文档 → 【7-4-7】再保险
4. **保险资管类**：投资管理、资产管理、资金运用等相关文档 → 【7-4-8】保险资管
5. **保险中介类**：代理、经纪、公估等相关文档 → 【7-4-9】保险中介
6. **新兴业态类**：互联网保险、科技保险、创新业务等相关文档 → 【7-4-10】新兴业态
7. **监管政策类**：保监会政策、监管规定、合规要求等相关文档 → 【7-4-2】保监会
8. **公司经营类**：公司管理、经营策略、市场分析等相关文档 → 【7-4-1】综合
9. **保险公司类**：具体保险公司相关文档 → 【7-4-4】保险公司

文件名关键词分析指导：
- 包含"寿险"、"健康险"、"意外险"、"年金"等 → 【7-4-5】人身险
- 包含"车险"、"家财险"、"责任险"、"工程险"等 → 【7-4-6】财产险
- 包含"再保险"、"分保"、"风险分散"等 → 【7-4-7】再保险
- 包含"投资"、"资管"、"资金运用"等 → 【7-4-8】保险资管
- 包含"代理"、"经纪"、"公估"等 → 【7-4-9】保险中介
- 包含"互联网"、"科技"、"创新"、"数字化"等 → 【7-4-10】新兴业态
- 包含"监管"、"政策"、"规定"、"合规"等 → 【7-4-2】保监会
- 包含具体公司名称（如"平安"、"国寿"、"太保"等） → 【7-4-4】保险公司
- 包含"经营"、"策略"、"分析"、"报告"等 → 【7-4-1】综合

分类要求：
1. 必须严格从上述文件夹路径列表中复制完整的路径
2. 不能修改、缩写或添加任何内容到路径
3. 不能创建或想象不存在的文件夹
4. 优先选择最具体的分类，避免选择过于宽泛的"综合"类
5. 按匹配度从高到低返回前三个路径
6. 每行一个路径，不要包含任何其他内容
7. 不要使用"<think>"标签或任何思考过程描述
8. 仔细分析文件名关键词，选择最匹配的专业分类
9. 优先参考用户自定义分类规则进行判断

输出格式（严格按此格式，每行一个完整路径）：
第一推荐：[完整路径1]
第二推荐：[完整路径2]
第三推荐：[完整路径3]

请开始推荐："""
            
            # 在传递给大模型的完整内容最尾部添加/no_think标签
            final_prompt = prompt + "\n\n/no_think"
            
            print(f"🤖 发送给AI的提示词:\n{final_prompt}")
            
            # 使用系统提示词来抑制思考过程
            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的保险行业文件分类专家。重要：不要输出任何推理过程、思考步骤或解释。直接按要求输出结果。只输出完整路径，不要包含任何其他信息。优先选择最具体的专业分类，避免选择过于宽泛的"综合"类。'
                },
                {
                    'role': 'user',
                    'content': final_prompt
                }
            ]
            
            result = self.ollama_client.chat_with_retry(messages)
            print(f"🤖 AI原始返回结果: {result}")
            
            # 清理结果中的思考过程（现在在_parse_classification_result中统一处理）
            result = result.strip()
            
            # 如果结果仍然以思考过程开头，尝试更激进的清理
            if any(keyword in result.lower() for keyword in ['好，', '嗯，', '我来', '我需要', '首先，', '让我']):
                # 找到第一个完整的句子
                sentences = result.split('。')
                if len(sentences) > 1:
                    # 跳过第一个句子（通常是思考过程），使用第二个句子开始
                    result = '。'.join(sentences[1:]).strip()
            
            # 解析AI分类结果
            recommended_folder, match_reason = self._parse_classification_result(result, target_directory)
            
            # 检查分类质量：如果推荐的是过于宽泛的分类，尝试重新分类
            broad_categories = ['【7-4-1】综合', '【7-4-1-4】经营业态']
            if recommended_folder and any(broad in recommended_folder for broad in broad_categories) and retry_count < 2:
                print(f"⚠️  AI推荐了过于宽泛的分类: {recommended_folder}，准备第 {retry_count + 1} 次重试...")
                logging.warning(f"AI推荐了过于宽泛的分类: {recommended_folder}，准备第 {retry_count + 1} 次重试")
                
                # 在重试时强调要选择更具体的分类
                return self._recommend_target_folder(file_path, content, summary, target_directory, retry_count + 1)
            
            # 检查是否匹配失败，如果是且未超过重试次数，则重试
            if recommended_folder is None and retry_count < 2:  # 最多重试2次
                print(f"⚠️  AI分类失败，准备第 {retry_count + 1} 次重试...")
                logging.warning(f"AI分类失败，准备第 {retry_count + 1} 次重试")
                
                # 递归调用自身进行重试
                return self._recommend_target_folder(file_path, content, summary, target_directory, retry_count + 1)
            
            return recommended_folder, match_reason
            
        except Exception as e:
            logging.error(f"推荐目标文件夹失败: {e}")
            return None, f"推荐失败: {str(e)}"
    def _extract_recommended_paths(self, ai_result: str) -> List[str]:
        """
        从AI返回结果中提取三个推荐路径
        
        Args:
            ai_result: AI返回的原始结果
            
        Returns:
            List[str]: 提取到的推荐路径列表
        """
        recommended_paths = []
        
        try:
            lines = ai_result.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 查找包含推荐路径的行
                if any(keyword in line for keyword in ['第一推荐：', '第二推荐：', '第三推荐：', '推荐：']):
                    # 提取冒号后的路径
                    if '：' in line:
                        path = line.split('：', 1)[1].strip()
                        if path and path not in recommended_paths:
                            recommended_paths.append(path)
                elif line.startswith('【') and '】' in line:
                    # 直接识别以【开头的路径格式
                    if line not in recommended_paths:
                        recommended_paths.append(line)
            
            # 如果没有找到格式化的推荐，尝试按行提取前三个有效路径
            if not recommended_paths:
                for line in lines:
                    line = line.strip()
                    if line and line.startswith('【') and '】' in line:
                        if line not in recommended_paths:
                            recommended_paths.append(line)
                        if len(recommended_paths) >= 3:
                            break
            
            # 限制最多返回3个路径
            return recommended_paths[:3]
            
        except Exception as e:
            logging.error(f"提取推荐路径时出错: {e}")
            return []
    
    def _parse_classification_result(self, result: str, target_directory: str) -> tuple:
        """
        解析AI分类结果，支持三个推荐路径的依次验证
        
        Args:
            result: AI返回的分类结果
            target_directory: 目标目录路径
            
        Returns:
            tuple: (推荐文件夹路径, 匹配理由)
        """
        try:
            result = result.strip()
            logging.info(f"正在解析AI分类结果: {result[:100]}...")
            
            print(f"🔍 解析AI分类结果: {result}")
            
            # 清理AI返回结果中的思考过程标签和内容
            result_clean = self._clean_ai_response(result)
            logging.info(f"清理后的分类结果: {result_clean[:100]}...")
            print(f"🧹 清理后的结果: {result_clean}")
            
            # 提取三个推荐路径
            recommended_paths = self._extract_recommended_paths(result_clean)
            
            if not recommended_paths:
                logging.warning(f"无法从AI结果中提取推荐路径")
                print(f"⚠️ 无法提取推荐路径")
                return None, f"AI智能分类失败，无法解析推荐路径: {result_clean[:50]}..."
            
            print(f"📋 提取到 {len(recommended_paths)} 个推荐路径: {recommended_paths}")
            
            # 依次验证每个推荐路径
            for i, recommended_path in enumerate(recommended_paths, 1):
                target_path = Path(target_directory) / recommended_path
                
                print(f"🔍 验证第{i}个推荐路径: {recommended_path}")
                print(f"🎯 完整目标路径: {target_path}")
                
                # 验证路径是否存在且为目录
                if target_path.exists() and target_path.is_dir():
                    logging.info(f"找到有效的目标文件夹(第{i}选择): {recommended_path}")
                    print(f"✅ 找到有效目标文件夹(第{i}选择): {recommended_path}")
                    
                    # 存储推荐的完整路径
                    self.recommended_folder_path = recommended_path
                    print(f"💾 存储推荐路径: {self.recommended_folder_path}")
                    
                    # 生成有意义的匹配理由
                    match_reason = f"AI智能分类(第{i}选择)：根据文件内容匹配到 {recommended_path}"
                    
                    return recommended_path, match_reason
                else:
                    logging.warning(f"第{i}个推荐路径不存在: {target_path}")
                    print(f"❌ 第{i}个推荐路径不存在: {recommended_path}")
            
            # 如果所有推荐路径都无效
            logging.error(f"所有推荐路径都无效: {recommended_paths}")
            print(f"💥 所有推荐路径都无效")
            
            return None, f"AI智能分类失败，三个推荐路径都不存在: {', '.join(recommended_paths[:3])}"
            
        except Exception as e:
            logging.error(f"解析分类结果失败: {e}, 原始结果: {result}")
            return None, f"解析分类结果时发生错误: {str(e)}"
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

    def preview_classification(self, source_directory: str, target_directory: str) -> List[Dict[str, object]]:
        try:
            source_files = self.scan_source_files(source_directory)
            if not source_files:
                raise FileOrganizerError("源目录中没有找到文件")
            preview_results = []
            logging.info(f"开始预览分类，共 {len(source_files)} 个文件")
            preview_count = len(source_files)
            for i, file_path in enumerate(source_files, 1):
                file_name = Path(file_path).name
                try:
                    logging.info(f"正在处理文件 {i}/{preview_count}: {file_name}")
                    print(f"\n=== 处理文件 {i}/{preview_count}: {file_name} ===")
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
            
            # 生成预览结果JSON文件（格式与preview_ai_result.json保持一致）
            try:
                ai_preview_results = []
                for result in preview_results:
                    if result['success']:
                        ai_preview_result = {
                            "源文件路径": result['file_path'],
                            "文件摘要": result['content_summary'],
                            "最匹配的目标目录": result['target_folder'],
                            "匹配理由": result['match_reason'],
                            "处理耗时信息": {
                                "总耗时(秒)": result['timing_info'].get('total_processing_time', 0),
                                "内容提取耗时(秒)": result['timing_info'].get('content_extraction_time', 0),
                                "摘要生成耗时(秒)": result['timing_info'].get('summary_generation_time', 0),
                                "目录推荐耗时(秒)": result['timing_info'].get('folder_recommendation_time', 0)
                            }
                        }
                        ai_preview_results.append(ai_preview_result)
                
                # 保存预览结果到JSON文件
                preview_result_file = 'preview_ai_result.json'
                with open(preview_result_file, 'w', encoding='utf-8') as f:
                    json.dump(ai_preview_results, f, ensure_ascii=False, indent=2)
                logging.info(f"AI预览结果已保存到: {preview_result_file}")
                
            except Exception as e:
                logging.warning(f"生成预览结果文件失败: {e}")
            
            return preview_results
        except Exception as e:
            raise FileOrganizerError(f"预览分类失败: {e}")
    def organize_file(self, file_path: str, target_directory: str) -> Tuple[bool, str]:
        try:
            if not self.ollama_client:
                self.initialize_ollama()
            
            file_path_obj = Path(file_path)
            filename = file_path_obj.name
            source_file_full_path = str(file_path_obj.absolute())
            
            print(f"📄 源文件完整路径: {source_file_full_path}")
            
            # 使用AI分类获取推荐文件夹
            target_folder, match_reason, success = self.classify_file(str(file_path_obj), target_directory)
            if not success or not target_folder:
                return False, "无法确定目标文件夹"
            
            # 使用存储的推荐路径变量
            if hasattr(self, 'recommended_folder_path') and self.recommended_folder_path:
                target_folder_full_path = Path(target_directory) / self.recommended_folder_path
                print(f"🔧 使用存储的推荐路径: {self.recommended_folder_path}")
                print(f"🎯 目标文件夹完整路径: {target_folder_full_path}")
            else:
                target_folder_full_path = Path(target_directory) / target_folder
                print(f"⚠️  使用默认路径: {target_folder}")
                print(f"🎯 目标文件夹完整路径: {target_folder_full_path}")
            
            # 构建完整的迁移命令信息
            migration_info = {
                'source_file': source_file_full_path,
                'target_folder': str(target_folder_full_path),
                'filename': filename,
                'match_reason': match_reason
            }
            
            print(f"📋 迁移信息: {migration_info}")
            
            # 创建目标文件夹
            target_folder_full_path.mkdir(parents=True, exist_ok=True)
            
            # 构建目标文件路径
            target_file_path = target_folder_full_path / filename
            if target_file_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    new_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                else:
                    new_filename = f"{filename}_{timestamp}"
                target_file_path = target_folder_full_path / new_filename
                print(f"⚠️  文件名冲突，重命名为: {new_filename}")
            
            # 执行文件复制
            shutil.copy2(source_file_full_path, str(target_file_path))
            
            # 记录迁移日志
            migration_log = f"文件迁移完成: {source_file_full_path} -> {target_file_path}"
            logging.info(migration_log)
            print(f"✅ {migration_log}")
            
            return True, str(target_file_path)
        except Exception as e:
            error_msg = f"整理文件失败: {e}"
            logging.error(error_msg)
            return False, error_msg
    def organize_files(self, files=None, target_base_dir=None, copy_mode=True, source_directory=None, target_directory=None, dry_run=False, progress_callback=None) -> Dict[str, object]:
        try:
            if source_directory and target_directory:
                files = self.scan_files(source_directory)
                target_base_dir = target_directory
                copy_mode = True
            if not files or not target_base_dir:
                raise FileOrganizerError("缺少必要参数")
            log_session_name = None
            if self.enable_transfer_log and self.transfer_log_manager and not dry_run:
                try:
                    session_name = f"organize_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    log_session_name = self.transfer_log_manager.start_transfer_session(session_name)
                    logging.info(f"开始转移日志会话: {session_name}")
                except Exception as e:
                    logging.warning(f"启动转移日志会话失败: {e}")
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
            
            # 初始化AI结果文件
            ai_result_file = 'ai_organize_result.json'
            # 不再在内存中保存完整的ai_results列表，只保存必要的迁移信息
            migration_queue = []  # 只保存源路径和目标路径的简单信息
            
            # 确保AI结果文件存在，但不清空现有内容
            if not os.path.exists(ai_result_file):
                with open(ai_result_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                logging.info(f"创建新的AI结果文件: {ai_result_file}")
            else:
                logging.info(f"AI结果文件已存在，将追加新记录: {ai_result_file}")
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
                    
                    # 获取详细的分析结果（只调用一次）
                    analysis_result = self.analyze_and_classify_file(file_path, target_base_dir)
                    target_folder = analysis_result.get('recommended_folder')
                    match_reason = analysis_result.get('match_reason', '')
                    success = analysis_result.get('success', False)
                    
                    results['ai_responses'].append({
                        'file_name': filename,
                        'target_folder': target_folder,
                        'match_reason': match_reason,
                        'success': success
                    })
                    
                    # 构建AI结果项（基础信息）
                    ai_result_item = {
                        "处理时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "文件名": filename,
                        "源文件路径": file_path,
                        "文件摘要": analysis_result.get('content_summary', ''),
                        "最匹配的目标目录": analysis_result.get('recommended_folder', ''),
                        "匹配理由": analysis_result.get('match_reason', ''),
                        "处理耗时信息": {
                            "总耗时(秒)": analysis_result.get('timing_info', {}).get('total_processing_time', 0),
                            "内容提取耗时(秒)": analysis_result.get('timing_info', {}).get('content_extraction_time', 0),
                            "摘要生成耗时(秒)": analysis_result.get('timing_info', {}).get('summary_generation_time', 0),
                            "目录推荐耗时(秒)": analysis_result.get('timing_info', {}).get('folder_recommendation_time', 0)
                        }
                    }
                    
                    # 保存到迁移队列，等待迁移成功后写入完整信息
                    migration_queue.append({
                        'source_path': file_path,
                        'target_folder': target_folder,
                        'filename': filename,
                        'match_reason': match_reason,
                        'ai_result_item': ai_result_item
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
                        
                        # 更新迁移队列中最后一项的失败状态并立即写入
                        if migration_queue:
                            migration_queue[-1]['ai_result_item'].update({
                                "处理状态": "分类失败",
                                "错误信息": match_reason
                            })
                            # 立即写入失败记录
                            self._append_ai_result_to_file(ai_result_file, migration_queue[-1]['ai_result_item'])
                        
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
                                
                                # 更新迁移队列中对应项的最终路径并立即写入
                                for queue_item in migration_queue:
                                    if queue_item['source_path'] == file_path:
                                        queue_item['ai_result_item'].update({
                                            "最终目标路径": str(target_file_path),
                                            "操作类型": operation_cn,
                                            "处理状态": "成功"
                                        })
                                        # 立即写入成功记录
                                        self._append_ai_result_to_file(ai_result_file, queue_item['ai_result_item'])
                                        break
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
                        
                        # 试运行模式下更新迁移队列中对应项并立即写入
                        for queue_item in migration_queue:
                            if queue_item['source_path'] == file_path:
                                queue_item['ai_result_item'].update({
                                    "最终目标路径": str(target_file_path),
                                    "操作类型": operation_cn,
                                    "处理状态": "试运行成功"
                                })
                                # 立即写入试运行记录
                                self._append_ai_result_to_file(ai_result_file, queue_item['ai_result_item'])
                                break
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
            
            # AI结果已在处理过程中实时写入
            results['ai_result_file'] = ai_result_file
            logging.info(f"AI分析结果已实时写入: {ai_result_file}")
            
            if self.enable_transfer_log and self.transfer_log_manager and not dry_run:
                try:
                    session_summary = self.transfer_log_manager.end_transfer_session()
                    logging.info(f"转移日志会话结束: {session_summary}")
                except Exception as e:
                    logging.warning(f"结束转移日志会话失败: {e}")
            
            logging.info(f"安全文件整理完成: 成功 {results['successful_moves']}, 失败 {results['failed_moves']}, 跳过 {results['skipped_files']}")
            
            # 删除源文件功能已移至GUI界面，不再在控制台询问
            if not dry_run and results['successful_moves'] > 0:
                logging.info(f"成功处理 {results['successful_moves']} 个文件，删除源文件功能请在GUI界面使用")
            
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
    def _append_ai_result_to_file(self, ai_result_file: str, ai_result_item: dict) -> None:
        """追加AI结果到文件，避免在内存中保存大量数据"""
        try:
            # 读取现有数据
            existing_data = []
            if os.path.exists(ai_result_file):
                try:
                    with open(ai_result_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:  # 只有当文件不为空时才尝试解析JSON
                            existing_data = json.loads(content)
                        else:
                            existing_data = []  # 空文件时初始化为空列表
                except json.JSONDecodeError:
                    # 如果JSON解析失败，初始化为空列表
                    existing_data = []
                    logging.warning(f"AI结果文件格式错误，重新初始化: {ai_result_file}")
            
            # 追加新数据
            existing_data.append(ai_result_item)
            
            # 写回文件
            with open(ai_result_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logging.error(f"追加AI结果到文件失败: {e}")
    
    def _update_last_ai_result(self, ai_result_file: str, updates: dict) -> None:
        """更新文件中最后一条AI结果记录"""
        try:
            # 读取现有数据
            existing_data = []
            if os.path.exists(ai_result_file):
                try:
                    with open(ai_result_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:  # 只有当文件不为空时才尝试解析JSON
                            existing_data = json.loads(content)
                        else:
                            existing_data = []  # 空文件时初始化为空列表
                except json.JSONDecodeError:
                    # 如果JSON解析失败，初始化为空列表
                    existing_data = []
                    logging.warning(f"AI结果文件格式错误，重新初始化: {ai_result_file}")
            
            # 更新最后一条记录
            if existing_data:
                existing_data[-1].update(updates)
                
                # 写回文件
                with open(ai_result_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            logging.error(f"更新AI结果文件失败: {e}")

    # def _ask_delete_source_files(self, successful_moves: List[Dict]) -> None:
    #     """询问用户是否删除源文件 - 已移至GUI界面，此方法不再使用"""
    #     # 删除源文件功能已移至GUI界面，不再在控制台询问
    #     pass

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
    
    def batch_read_documents(self, folder_path: str, progress_callback=None, summary_length: int = 200) -> Dict[str, Any]:
        """
        批量解读文件夹下所有文档，生成摘要并保存到AI结果文件
        
        Args:
            folder_path: 要解读的文件夹路径
            progress_callback: 进度回调函数，接收 (current, total, filename) 参数
            summary_length: 摘要长度（字数），默认200字
            
        Returns:
            包含处理结果的字典
        """
        start_time = time.time()
        timing_info = {}
        
        try:
            if not self.ollama_client:
                init_start = time.time()
                self.initialize_ollama()
                timing_info['ollama_init_time'] = round(time.time() - init_start, 3)
            
            folder_path = Path(folder_path)
            if not folder_path.exists() or not folder_path.is_dir():
                raise FileOrganizerError(f"文件夹不存在或不是有效目录: {folder_path}")
            
            # 支持的文档格式
            supported_extensions = {'.txt', '.pdf', '.docx', '.doc', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'}
            
            # 扫描文件夹获取所有支持的文档文件
            document_files = []
            for file_path in folder_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    document_files.append(file_path)
            
            if not document_files:
                return {
                    'total_files': 0,
                    'processed_files': 0,
                    'successful_reads': 0,
                    'failed_reads': 0,
                    'errors': [],
                    'timing_info': timing_info,
                    'start_time': datetime.now(),
                    'end_time': datetime.now()
                }
            
            # 初始化结果统计
            results = {
                'total_files': len(document_files),
                'processed_files': 0,
                'successful_reads': 0,
                'failed_reads': 0,
                'errors': [],
                'timing_info': timing_info,
                'start_time': datetime.now(),
                'end_time': None
            }
            
            # 初始化AI结果文件
            ai_result_file = 'ai_organize_result.json'
            if not os.path.exists(ai_result_file):
                with open(ai_result_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                logging.info(f"创建新的AI结果文件: {ai_result_file}")
            else:
                logging.info(f"AI结果文件已存在，将追加新记录: {ai_result_file}")
            

            
            logging.info(f"开始批量文档解读，共 {len(document_files)} 个文件")
            print(f"\n=== 开始批量文档解读 ===")
            print(f"源文件夹: {folder_path}")
            print(f"待处理文件总数: {len(document_files)}")
            print("=" * 50)
            
            # 逐个处理文档文件
            for i, file_path in enumerate(document_files, 1):
                filename = file_path.name
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(i, len(document_files), filename)
                
                # 控制台输出当前处理进度
                print(f"\n[{i}/{len(document_files)}] 正在解读: {filename}")
                
                try:
                    logging.info(f"正在解读文件 {i}/{len(document_files)}: {filename}")
                    print(f"  📖 正在提取文件内容...", end="", flush=True)
                    
                    # 提取文件内容
                    extract_start = time.time()
                    extracted_content = self._extract_file_content(str(file_path))
                    extract_time = round(time.time() - extract_start, 3)
                    
                    # 根据设置截取内容用于AI处理
                    truncate_length = self.ai_parameters['content_extraction_length'] if self.ai_parameters['content_extraction_length'] < 2000 else len(extracted_content)
                    content_for_ai = extracted_content[:truncate_length] if extracted_content else ""
                    
                    print(f"\r  📖 正在生成摘要...", end="", flush=True)
                    
                    # 生成摘要
                    summary_start = time.time()
                    summary = self._generate_content_summary(content_for_ai, filename, summary_length)
                    summary_time = round(time.time() - summary_start, 3)
                    
                    print(f"\r  ✅ 解读完成")
                    print(f"     摘要: {summary[:100]}{'...' if len(summary) > 100 else ''}")
                    
                    # 构建AI结果项（与迁移功能格式兼容）
                    ai_result_item = {
                        "处理时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "文件名": filename,
                        "源文件路径": str(file_path),  # 这里作为目标路径，因为文件已在目标位置
                        "文件摘要": summary,
                        "最匹配的目标目录": str(file_path.parent),  # 当前文件夹作为目标目录
                        "匹配理由": "批量文档解读",
                        "处理耗时信息": {
                            "总耗时(秒)": round(extract_time + summary_time, 3),
                            "内容提取耗时(秒)": extract_time,
                            "摘要生成耗时(秒)": summary_time,
                            "目录推荐耗时(秒)": 0
                        },
                        "最终目标路径": str(file_path),  # 文件当前位置就是最终位置
                        "操作类型": "文档解读",
                        "处理状态": "解读成功"
                    }
                    
                    # 保存到AI结果文件
                    self._append_ai_result_to_file(ai_result_file, ai_result_item)
                    
                    results['successful_reads'] += 1
                    logging.info(f"文档解读成功: {filename}，摘要长度: {len(summary)} 字符")
                    
                except Exception as e:
                    error_msg = f"解读文件 {filename} 时出错: {str(e)}"
                    print(f"\r  ❌ 解读失败: {str(e)}")
                    logging.error(error_msg)
                    results['errors'].append(error_msg)
                    results['failed_reads'] += 1
                    
                    # 保存失败记录
                    try:
                        ai_result_item = {
                            "处理时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "文件名": filename,
                            "源文件路径": str(file_path),
                            "文件摘要": "",
                            "最匹配的目标目录": str(file_path.parent),
                            "匹配理由": "批量文档解读",
                            "处理耗时信息": {
                                "总耗时(秒)": 0,
                                "内容提取耗时(秒)": 0,
                                "摘要生成耗时(秒)": 0,
                                "目录推荐耗时(秒)": 0
                            },
                            "最终目标路径": str(file_path),
                            "操作类型": "文档解读",
                            "处理状态": "解读失败",
                            "错误信息": str(e)
                        }
                        self._append_ai_result_to_file(ai_result_file, ai_result_item)
                    except Exception as save_error:
                        logging.warning(f"保存失败记录时出错: {save_error}")
                
                finally:
                    results['processed_files'] += 1
            
            results['end_time'] = datetime.now()
            
            # 输出处理完成总结
            print(f"\n=== 批量文档解读完成 ===")
            print(f"总文件数: {results['total_files']}")
            print(f"成功解读: {results['successful_reads']} 个")
            print(f"解读失败: {results['failed_reads']} 个")
            duration = (results['end_time'] - results['start_time']).total_seconds()
            print(f"总耗时: {duration:.1f} 秒")
            print("=" * 50)
            
            logging.info(f"批量文档解读完成: 成功 {results['successful_reads']}, 失败 {results['failed_reads']}")
            logging.info(f"解读结果已保存到: {ai_result_file}")
            
            return results
            
        except Exception as e:
            raise FileOrganizerError(f"批量文档解读失败: {e}")