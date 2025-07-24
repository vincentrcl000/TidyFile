#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一AI客户端管理器

功能：
- 根据用户配置的模型列表按优先级调用
- 支持多种AI服务（Qwen-Long、Ollama、OpenAI等）
- 失败时自动尝试下一个模型
- 统一的接口，简化调用
- JSON配置文件支持

作者: AI Assistant
创建时间: 2025-01-15
"""

import logging
import time
import json
import os
from typing import Dict, List, Optional, Any

class AIClientError(Exception):
    """AI客户端异常"""
    pass

class ModelConfig:
    """AI模型配置"""
    def __init__(self, id: str, name: str, base_url: str, model_name: str, model_type: str, api_key: str, priority: int, enabled: bool = True):
        self.id = id
        self.name = name
        self.base_url = base_url
        self.model_name = model_name
        self.model_type = model_type
        self.api_key = api_key
        self.priority = priority
        self.enabled = enabled

class AIClient:
    """AI客户端基类"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化客户端"""
        raise NotImplementedError
    
    def chat_with_retry(self, messages: List[Dict], max_retries: int = 3) -> str:
        """与模型对话，支持重试机制"""
        raise NotImplementedError
    
    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        raise NotImplementedError

class OpenAICompatibleClient(AIClient):
    """OpenAI兼容模型客户端（适用于Qwen-Long等）"""
    
    def _initialize_client(self):
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        except ImportError:
            raise AIClientError("需要安装openai库: pip install openai")
        except Exception as e:
            raise AIClientError(f"初始化OpenAI兼容客户端失败: {e}")
    
    def chat_with_retry(self, messages: List[Dict], max_retries: int = 3) -> str:
        """与OpenAI兼容模型对话，支持重试机制"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logging.info(f"尝试使用OpenAI兼容模型 (第{attempt + 1}次)")
                
                # 根据模型类型决定是否使用enable_thinking参数
                extra_params = {}
                if "qwen" in self.config.model_name.lower():
                    extra_params["extra_body"] = {"enable_thinking": False}
                
                completion = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=messages,
                    **extra_params
                )
                
                if completion.choices and len(completion.choices) > 0:
                    content = completion.choices[0].message.content.strip()
                    if content:
                        logging.info("OpenAI兼容模型响应成功")
                        return content
                    else:
                        raise AIClientError("OpenAI兼容模型返回空内容")
                else:
                    raise AIClientError("OpenAI兼容模型返回无效响应格式")
                    
            except Exception as e:
                last_error = e
                logging.warning(f"OpenAI兼容模型响应失败 (第{attempt + 1}次): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
        
        error_msg = f"OpenAI兼容模型所有重试都失败，最后错误: {last_error}"
        logging.error(error_msg)
        raise AIClientError(error_msg)
    
    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        result = {'success': False, 'error': None, 'response_time': None}
        
        try:
            start_time = time.time()
            
            # 使用requests直接调用API，禁用代理
            try:
                import requests
                import os
                # 禁用代理
                os.environ['NO_PROXY'] = '*'
                headers = {'Authorization': f'Bearer {self.config.api_key}'} if self.config.api_key else {}
                response = requests.get(
                    f"{self.config.base_url}/models", 
                    headers=headers, 
                    timeout=10,
                    proxies={'http': None, 'https': None}
                )
                if response.status_code != 200:
                    result['error'] = f"API请求失败，状态码: {response.status_code}"
                    return result
                
                models_data = response.json()
                if not models_data or not models_data.get('data'):
                    result['error'] = "无法获取模型列表"
                    return result
                
                # 检查目标模型是否存在
                available_models = [m.get('id', '') for m in models_data['data']]
                if self.config.model_name not in available_models:
                    result['error'] = f"模型 {self.config.model_name} 不存在，可用模型: {available_models[:3]}"
                    return result
                
                result['success'] = True
                result['response_time'] = round(time.time() - start_time, 3)
                
            except requests.exceptions.ConnectionError:
                result['error'] = f"Failed to connect to OpenAI compatible API. Please check the service is accessible at {self.config.base_url}"
            except requests.exceptions.Timeout:
                result['error'] = "连接超时，请检查服务是否正常运行"
            except Exception as e:
                result['error'] = f"连接失败: {str(e)}"
                
        except Exception as e:
            result['error'] = str(e)
        
        return result

class QwenLongClient(OpenAICompatibleClient):
    """Qwen-Long在线模型客户端（继承自OpenAICompatibleClient）"""
    pass

class OllamaClient(AIClient):
    """Ollama模型客户端"""
    
    def _initialize_client(self):
        try:
            import ollama
            # 从base_url中提取host
            if self.config.base_url.startswith('http://'):
                host = self.config.base_url
            else:
                host = f"http://{self.config.base_url}"
            self.client = ollama.Client(host=host)
        except ImportError:
            raise AIClientError("需要安装ollama库: pip install ollama")
        except Exception as e:
            raise AIClientError(f"初始化Ollama客户端失败: {e}")
    
    def chat_with_retry(self, messages: List[Dict], max_retries: int = 3) -> str:
        """与Ollama模型对话，支持重试机制"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logging.info(f"尝试使用Ollama模型 (第{attempt + 1}次)")
                
                # 使用requests直接调用API
                import requests
                import json
                
                # 准备请求数据
                payload = {
                    "model": self.config.model_name,
                    "messages": messages,
                    "stream": False
                }
                
                response = requests.post(
                    f"{self.config.base_url}/api/chat",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code != 200:
                    raise AIClientError(f"API请求失败，状态码: {response.status_code}, 响应: {response.text}")
                
                response_data = response.json()
                
                if response_data and 'message' in response_data:
                    content = response_data['message']['content'].strip()
                    if content:
                        logging.info("Ollama模型响应成功")
                        return content
                    else:
                        raise AIClientError("Ollama模型返回空内容")
                else:
                    raise AIClientError("Ollama模型返回无效响应格式")
                    
            except requests.exceptions.ConnectionError as e:
                last_error = f"Failed to connect to Ollama. Please check that Ollama is downloaded, running and accessible. https://ollama.com/download"
                logging.warning(f"Ollama模型响应失败 (第{attempt + 1}次): {last_error}")
            except requests.exceptions.Timeout as e:
                last_error = f"连接超时: {str(e)}"
                logging.warning(f"Ollama模型响应失败 (第{attempt + 1}次): {last_error}")
            except Exception as e:
                last_error = e
                logging.warning(f"Ollama模型响应失败 (第{attempt + 1}次): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
        
        error_msg = f"Ollama模型所有重试都失败，最后错误: {last_error}"
        logging.error(error_msg)
        raise AIClientError(error_msg)
    
    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        result = {'success': False, 'error': None, 'response_time': None}
        
        try:
            start_time = time.time()
            
            # 使用requests直接调用API
            try:
                import requests
                response = requests.get(f"{self.config.base_url}/api/tags", timeout=10)
                if response.status_code != 200:
                    result['error'] = f"API请求失败，状态码: {response.status_code}"
                    return result
                
                models_data = response.json()
                if not models_data or not models_data.get('models'):
                    result['error'] = "无法获取模型列表"
                    return result
                
                # 检查目标模型是否存在
                available_models = [m.get('name', '') for m in models_data['models']]
                if self.config.model_name not in available_models:
                    result['error'] = f"模型 {self.config.model_name} 不存在，可用模型: {available_models[:3]}"
                    return result
                
                result['success'] = True
                result['response_time'] = round(time.time() - start_time, 3)
                
            except requests.exceptions.ConnectionError:
                result['error'] = f"Failed to connect to Ollama. Please check that Ollama is downloaded, running and accessible. https://ollama.com/download"
            except requests.exceptions.Timeout:
                result['error'] = "连接超时，请检查Ollama服务是否正常运行"
            except Exception as e:
                result['error'] = f"连接失败: {str(e)}"
                
        except Exception as e:
            result['error'] = str(e)
        
        return result

class LMStudioClient(AIClient):
    """LM Studio模型客户端（兼容OpenAI API）"""
    
    def _initialize_client(self):
        try:
            from openai import OpenAI
            # LM Studio使用OpenAI兼容的API
            self.client = OpenAI(
                api_key="not-needed",  # LM Studio不需要API密钥
                base_url=self.config.base_url,
            )
        except ImportError:
            raise AIClientError("需要安装openai库: pip install openai")
        except Exception as e:
            raise AIClientError(f"初始化LM Studio客户端失败: {e}")
    
    def chat_with_retry(self, messages: List[Dict], max_retries: int = 3) -> str:
        """与LM Studio模型对话，支持重试机制"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logging.info(f"尝试使用LM Studio模型 (第{attempt + 1}次)")
                
                completion = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.7
                )
                
                if completion.choices and len(completion.choices) > 0:
                    content = completion.choices[0].message.content.strip()
                    if content:
                        logging.info("LM Studio模型响应成功")
                        return content
                    else:
                        raise AIClientError("LM Studio模型返回空内容")
                else:
                    raise AIClientError("LM Studio模型返回无效响应格式")
                    
            except Exception as e:
                last_error = e
                logging.warning(f"LM Studio模型响应失败 (第{attempt + 1}次): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
        
        error_msg = f"LM Studio模型所有重试都失败，最后错误: {last_error}"
        logging.error(error_msg)
        raise AIClientError(error_msg)
    
    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        result = {'success': False, 'error': None, 'response_time': None}
        
        try:
            start_time = time.time()
            
            # 使用requests直接调用API
            try:
                import requests
                response = requests.get(f"{self.config.base_url}/models", timeout=10)
                if response.status_code != 200:
                    result['error'] = f"API请求失败，状态码: {response.status_code}"
                    return result
                
                models_data = response.json()
                if not models_data or not models_data.get('data'):
                    result['error'] = "无法获取模型列表"
                    return result
                
                # 检查目标模型是否存在
                available_models = [m.get('id', '') for m in models_data['data']]
                if self.config.model_name not in available_models:
                    result['error'] = f"模型 {self.config.model_name} 不存在，可用模型: {available_models[:3]}"
                    return result
                
                result['success'] = True
                result['response_time'] = round(time.time() - start_time, 3)
                
            except requests.exceptions.ConnectionError:
                result['error'] = f"Failed to connect to LM Studio. Please check that LM Studio is running and accessible at {self.config.base_url}"
            except requests.exceptions.Timeout:
                result['error'] = "连接超时，请检查LM Studio服务是否正常运行"
            except Exception as e:
                result['error'] = f"连接失败: {str(e)}"
                
        except Exception as e:
            result['error'] = str(e)
        
        return result

class AIClientManager:
    """AI客户端管理器"""
    
    def __init__(self, config_file: str = "ai_models_config.json"):
        self.config_file = config_file
        self.models = []
        self.clients = {}
        self.load_config()
        self._initialize_clients()
    
    def load_config(self):
        """从JSON文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                self.models = []
                for model_data in config_data.get('models', []):
                    # 兼容旧版本配置（没有model_type字段）
                    model_type = model_data.get('model_type', '')
                    if not model_type:
                        # 根据base_url自动推断模型类型
                        base_url = model_data.get('base_url', '').lower()
                        if 'dashscope.aliyuncs.com' in base_url:
                            model_type = 'qwen_long'
                        elif ':1234' in base_url or 'lm studio' in model_data.get('name', '').lower():
                            model_type = 'lm_studio'
                        elif ':11434' in base_url or 'ollama' in model_data.get('name', '').lower():
                            model_type = 'ollama'
                        else:
                            model_type = 'openai_compatible'
                    
                    model = ModelConfig(
                        id=model_data.get('id', ''),
                        name=model_data.get('name', ''),
                        base_url=model_data.get('base_url', ''),
                        model_name=model_data.get('model_name', ''),
                        model_type=model_type,
                        api_key=model_data.get('api_key', ''),
                        priority=model_data.get('priority', 1),
                        enabled=model_data.get('enabled', True)
                    )
                    self.models.append(model)
                
                logging.info(f"从配置文件加载了 {len(self.models)} 个模型")
            else:
                # 创建默认配置
                self.create_default_config()
                
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            self.create_default_config()
    
    def create_default_config(self):
        """创建默认配置"""
        self.models = [
            ModelConfig('qwen-long', 'Qwen-Long在线模型', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'qwen-long', 'sk-9b728f2f153f4a81b507caeced3380d1', 1, True),
            ModelConfig('ollama-local', '本地Ollama模型', 'http://localhost:11434', 'qwen3:0.6b', '', 2, True)
        ]
        self.save_config()
        logging.info("创建了默认配置")
    
    def save_config(self):
        """保存配置到JSON文件"""
        try:
            config_data = {
                'models': [
                    {
                        'id': model.id,
                        'name': model.name,
                        'base_url': model.base_url,
                        'model_name': model.model_name,
                        'model_type': model.model_type,
                        'api_key': model.api_key,
                        'priority': model.priority,
                        'enabled': model.enabled
                    }
                    for model in self.models
                ]
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"配置已保存到 {self.config_file}")
            
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")
            raise AIClientError(f"保存配置文件失败: {e}")
    
    def _initialize_clients(self):
        """初始化所有客户端，自动启用可用的模型，禁用不可用的模型"""
        self.clients.clear()
        models_to_disable = []
        models_to_enable = []
        
        # 检查所有模型（包括已禁用和已启用的）
        for model in self.models:
            try:
                logging.info(f"正在检查模型: {model.name} ({model.base_url})")
                
                # 检查模型是否可用
                model_check = self._check_model_availability(model)
                if model_check['available']:
                    # 模型可用，尝试创建客户端
                    client = self._create_client(model)
                    if client:
                        self.clients[model.id] = client
                        logging.info(f"成功初始化客户端: {model.name}")
                        
                        # 如果模型当前是禁用状态，标记为需要启用
                        if not model.enabled:
                            models_to_enable.append(model.id)
                            logging.info(f"发现可用模型，将自动启用: {model.name}")
                    else:
                        logging.warning(f"创建客户端失败，将保持禁用状态: {model.name}")
                        if not model.enabled:
                            models_to_disable.append(model.id)
                else:
                    # 模型不可用
                    logging.warning(f"模型不可用: {model.name} - {model_check['error']}")
                    if model_check.get('available_models'):
                        logging.info(f"可用模型: {model_check['available_models'][:5]}")
                    
                    # 如果模型当前是启用状态，标记为需要禁用
                    if model.enabled:
                        models_to_disable.append(model.id)
                        logging.warning(f"模型不可用，将自动禁用: {model.name}")
                        
            except Exception as e:
                logging.warning(f"检查模型失败 {model.name}: {e}")
                if model.enabled:
                    models_to_disable.append(model.id)
                    logging.warning(f"检查失败，将自动禁用: {model.name}")
        
        # 自动启用可用的模型
        if models_to_enable:
            for model_id in models_to_enable:
                for model in self.models:
                    if model.id == model_id:
                        model.enabled = True
                        logging.info(f"已自动启用可用模型: {model.name}")
                        break
        
        # 自动禁用不可用的模型
        if models_to_disable:
            for model_id in models_to_disable:
                for model in self.models:
                    if model.id == model_id:
                        model.enabled = False
                        logging.info(f"已自动禁用不可用模型: {model.name}")
                        break
        
        # 如果有任何状态变化，保存配置
        if models_to_enable or models_to_disable:
            self.save_config()
            
            # 统计可用模型数量
            available_count = len(self.clients)
            total_enabled = len([m for m in self.models if m.enabled])
            logging.info(f"模型初始化完成: {available_count}/{total_enabled} 个模型可用")
            
            if available_count == 0:
                logging.warning("警告: 没有可用的AI模型，AI功能将无法使用")
            else:
                logging.info(f"可用模型列表: {[m.name for m in self.models if m.enabled]}")
        else:
            logging.info(f"所有模型状态正常，共 {len(self.clients)} 个可用模型")
    
    def _check_model_availability(self, model: ModelConfig) -> Dict[str, Any]:
        """检查模型是否可用"""
        result = {
            'available': False,
            'error': None,
            'available_models': [],
            'suggestions': []
        }
        
        try:
            # 根据模型类型进行不同的检查
            if model.model_type == "qwen_long":
                return self._check_qwen_long_availability(model)
            
            elif model.model_type == "lm_studio":
                return self._check_lm_studio_availability(model)
            
            elif model.model_type == "ollama":
                return self._check_ollama_availability(model)
            
            elif model.model_type == "openai_compatible":
                return self._check_generic_availability(model)
            
            else:
                result['error'] = f"未知的模型类型: {model.model_type}"
                result['suggestions'] = ["检查模型类型配置"]
                return result
                
        except Exception as e:
            result['error'] = f"检查模型可用性时出错: {e}"
            return result
    
    def _check_qwen_long_availability(self, model: ModelConfig) -> Dict[str, Any]:
        """检查Qwen-Long模型可用性"""
        result = {
            'available': False,
            'error': None,
            'available_models': [],
            'suggestions': []
        }
        
        try:
            import requests
            
            # 使用requests直接调用API
            headers = {'Authorization': f'Bearer {model.api_key}'} if model.api_key else {}
            response = requests.get(f"{model.base_url}/models", headers=headers, timeout=10)
            if response.status_code != 200:
                result['error'] = f"API请求失败，状态码: {response.status_code}"
                result['suggestions'] = ["检查API密钥是否有效", "检查网络连接"]
                return result
            
            models_data = response.json()
            if not models_data or not models_data.get('data'):
                result['error'] = "无法获取模型列表"
                result['suggestions'] = ["检查API密钥是否有效", "检查网络连接"]
                return result
            
            available_models = [m.get('id', '') for m in models_data['data']]
            result['available_models'] = available_models
            
            # 检查目标模型是否存在
            if model.model_name in available_models:
                result['available'] = True
            else:
                result['error'] = f"模型 {model.model_name} 不存在"
                result['suggestions'] = [
                    f"可用模型: {available_models[:5]}",
                    "检查模型名称是否正确",
                    "联系阿里云技术支持"
                ]
                
        except requests.exceptions.ConnectionError:
            result['error'] = f"Failed to connect to Qwen-Long API. Please check the service is accessible at {model.base_url}"
            result['suggestions'] = ["检查网络连接", "检查服务状态"]
        except requests.exceptions.Timeout:
            result['error'] = "连接超时，请检查Qwen-Long服务是否正常运行"
            result['suggestions'] = ["检查网络连接", "检查服务状态"]
        except Exception as e:
            result['error'] = str(e)
            result['suggestions'] = ["检查API密钥", "检查网络连接", "检查服务地址"]
        
        return result
    
    def _check_ollama_availability(self, model: ModelConfig) -> Dict[str, Any]:
        """检查Ollama模型可用性"""
        result = {
            'available': False,
            'error': None,
            'available_models': [],
            'suggestions': [],
            'mapped_model_name': None
        }
        
        try:
            import requests
            
            # 获取模型列表
            response = requests.get(f"{model.base_url}/api/tags", timeout=10)
            if response.status_code != 200:
                result['error'] = f"HTTP错误: {response.status_code}"
                result['suggestions'] = ["检查Ollama服务是否启动", "检查端口是否正确"]
                return result
            
            models_data = response.json()
            if not models_data or not models_data.get('models'):
                result['error'] = "无法获取模型列表"
                result['suggestions'] = ["检查Ollama服务状态", "重启Ollama服务"]
                return result
            
            available_models = [m.get('name', '') for m in models_data['models']]
            result['available_models'] = available_models
            
            # 智能模型名称匹配
            matched_model_name = self._find_matching_model(model.model_name, available_models, model.model_type)
            result['mapped_model_name'] = matched_model_name
            
            # 检查目标模型是否存在
            if matched_model_name in available_models:
                result['available'] = True
                if matched_model_name != model.model_name:
                    result['suggestions'] = [
                        f"模型名称已匹配: {model.model_name} -> {matched_model_name}",
                        "建议更新配置文件中的模型名称"
                    ]
            else:
                result['error'] = f"模型 {model.model_name} 不存在，匹配后 {matched_model_name} 也不存在"
                result['suggestions'] = [
                    f"可用模型: {available_models[:5]}",
                    f"下载模型: ollama pull {matched_model_name}",
                    "检查模型名称是否正确"
                ]
                
        except Exception as e:
            result['error'] = str(e)
            result['suggestions'] = ["检查Ollama服务", "检查网络连接", "检查端口设置"]
        
        return result
    
    def _check_lm_studio_availability(self, model: ModelConfig) -> Dict[str, Any]:
        """检查LM Studio模型可用性"""
        result = {
            'available': False,
            'error': None,
            'available_models': [],
            'suggestions': [],
            'mapped_model_name': None
        }
        
        try:
            import requests
            
            # 使用requests直接调用API
            response = requests.get(f"{model.base_url}/models", timeout=10)
            if response.status_code != 200:
                result['error'] = f"API请求失败，状态码: {response.status_code}"
                result['suggestions'] = ["检查LM Studio是否启动", "检查Local Server是否开启"]
                return result
            
            models_data = response.json()
            if not models_data or not models_data.get('data'):
                result['error'] = "无法获取模型列表"
                result['suggestions'] = ["检查LM Studio是否启动", "检查Local Server是否开启"]
                return result
            
            available_models = [m.get('id', '') for m in models_data['data']]
            result['available_models'] = available_models
            
            # 智能模型名称匹配
            matched_model_name = self._find_matching_model(model.model_name, available_models, model.model_type)
            result['mapped_model_name'] = matched_model_name
            
            # 检查目标模型是否存在
            if matched_model_name in available_models:
                result['available'] = True
                if matched_model_name != model.model_name:
                    result['suggestions'] = [
                        f"模型名称已匹配: {model.model_name} -> {matched_model_name}",
                        "建议更新配置文件中的模型名称"
                    ]
            else:
                result['error'] = f"模型 {model.model_name} 不存在，匹配后 {matched_model_name} 也不存在"
                result['suggestions'] = [
                    f"可用模型: {available_models[:5]}",
                    "在LM Studio中加载模型",
                    "检查模型是否已下载"
                ]
                
        except requests.exceptions.ConnectionError:
            result['error'] = f"Failed to connect to LM Studio. Please check that LM Studio is running and accessible at {model.base_url}"
            result['suggestions'] = ["检查LM Studio服务", "检查Local Server设置", "检查端口配置"]
        except requests.exceptions.Timeout:
            result['error'] = "连接超时，请检查LM Studio服务是否正常运行"
            result['suggestions'] = ["检查网络连接", "检查LM Studio服务状态"]
        except Exception as e:
            result['error'] = str(e)
            result['suggestions'] = ["检查LM Studio服务", "检查Local Server设置", "检查端口配置"]
        
        return result
    
    def _check_generic_availability(self, model: ModelConfig) -> Dict[str, Any]:
        """检查通用模型可用性"""
        result = {
            'available': False,
            'error': None,
            'available_models': [],
            'suggestions': []
        }
        
        try:
            import requests
            import os
            # 禁用代理
            os.environ['NO_PROXY'] = '*'
            
            # 使用requests直接调用API
            headers = {'Authorization': f'Bearer {model.api_key}'} if model.api_key else {}
            response = requests.get(
                f"{model.base_url}/models", 
                headers=headers, 
                timeout=10,
                proxies={'http': None, 'https': None}
            )
            if response.status_code != 200:
                result['error'] = f"API请求失败，状态码: {response.status_code}"
                result['suggestions'] = ["检查服务配置", "检查网络连接"]
                return result
            
            models_data = response.json()
            if not models_data or not models_data.get('data'):
                result['error'] = "无法获取模型列表"
                result['suggestions'] = ["检查服务配置", "检查网络连接"]
                return result
            
            available_models = [m.get('id', '') for m in models_data['data']]
            result['available_models'] = available_models
            
            # 检查目标模型是否存在
            if model.model_name in available_models:
                result['available'] = True
            else:
                result['error'] = f"模型 {model.model_name} 不存在"
                result['suggestions'] = [
                    f"可用模型: {available_models[:5]}",
                    "检查模型名称配置"
                ]
                
        except requests.exceptions.ConnectionError:
            result['error'] = f"Failed to connect to API. Please check the service is accessible at {model.base_url}"
            result['suggestions'] = ["检查网络连接", "检查服务状态"]
        except requests.exceptions.Timeout:
            result['error'] = "连接超时，请检查服务是否正常运行"
            result['suggestions'] = ["检查网络连接", "检查服务状态"]
        except Exception as e:
            result['error'] = str(e)
            result['suggestions'] = ["检查服务配置", "检查网络连接", "检查API密钥"]
        
        return result
    
    def _find_matching_model(self, user_model_name: str, available_models: List[str], model_type: str) -> str:
        """根据模型类型和用户输入，在可用模型中查找匹配的模型
        
        Args:
            user_model_name: 用户输入的模型名称
            available_models: 实际可用的模型列表
            model_type: 模型类型 (qwen_long, ollama, lm_studio, openai_compatible)
        
        Returns:
            匹配的模型名称，如果没有匹配则返回第一个可用模型
        """
        import re
        
        # 如果用户输入的模型名称直接存在，直接返回
        if user_model_name in available_models:
            return user_model_name
        
        user_model_lower = user_model_name.lower()
        
        # 根据模型类型进行不同的匹配策略
        if model_type == "lm_studio":
            # LM Studio 模型匹配策略
            # 1. 优先匹配 qwen/qwen3-8b 格式
            qwen_qwen3_8b = [m for m in available_models if 'qwen/qwen3-8b' in m.lower()]
            if qwen_qwen3_8b:
                logging.info(f"LM Studio 匹配: {user_model_name} -> {qwen_qwen3_8b[0]}")
                return qwen_qwen3_8b[0]
            
            # 2. 从用户输入中提取模型信息，构建LM Studio格式
            # 例如: qwen3:8b -> qwen/qwen3-8b
            # 例如: qwen3-8b -> qwen/qwen3-8b
            # 例如: qwen3.8b -> qwen/qwen3-8b
            qwen_pattern = r'qwen3[:\-\.]?(\d+b)'
            match = re.search(qwen_pattern, user_model_lower)
            if match:
                size = match.group(1)
                target_format = f"qwen/qwen3-{size}"
                if target_format in available_models:
                    logging.info(f"LM Studio 格式转换: {user_model_name} -> {target_format}")
                    return target_format
                
                # 尝试其他可能的格式
                for model in available_models:
                    if f"qwen3-{size}" in model.lower() or f"qwen3:{size}" in model.lower():
                        logging.info(f"LM Studio 大小匹配: {user_model_name} -> {model}")
                        return model
            
            # 3. 匹配其他 qwen3 系列
            qwen3_models = [m for m in available_models if 'qwen3' in m.lower()]
            if qwen3_models:
                logging.info(f"LM Studio qwen3系列匹配: {user_model_name} -> {qwen3_models[0]}")
                return qwen3_models[0]
        
        elif model_type == "ollama":
            # Ollama 模型匹配策略
            # 1. 优先匹配 qwen3:8b 格式
            qwen3_8b = [m for m in available_models if 'qwen3:8b' in m.lower()]
            if qwen3_8b:
                logging.info(f"Ollama 匹配: {user_model_name} -> {qwen3_8b[0]}")
                return qwen3_8b[0]
            
            # 2. 从用户输入中提取模型信息，构建Ollama格式
            # 例如: qwen/qwen3-8b -> qwen3:8b
            # 例如: qwen3-8b -> qwen3:8b
            qwen_pattern = r'qwen3[:\-\.]?(\d+b)'
            match = re.search(qwen_pattern, user_model_lower)
            if match:
                size = match.group(1)
                target_format = f"qwen3:{size}"
                if target_format in available_models:
                    logging.info(f"Ollama 格式转换: {user_model_name} -> {target_format}")
                    return target_format
                
                # 尝试其他可能的格式
                for model in available_models:
                    if f"qwen3-{size}" in model.lower() or f"qwen3:{size}" in model.lower():
                        logging.info(f"Ollama 大小匹配: {user_model_name} -> {model}")
                        return model
            
            # 3. 匹配其他 qwen3 系列
            qwen3_models = [m for m in available_models if 'qwen3' in m.lower()]
            if qwen3_models:
                logging.info(f"Ollama qwen3系列匹配: {user_model_name} -> {qwen3_models[0]}")
                return qwen3_models[0]
        
        elif model_type == "qwen_long":
            # Qwen-Long 模型匹配策略
            # 直接匹配 qwen-long
            qwen_long = [m for m in available_models if 'qwen-long' in m.lower()]
            if qwen_long:
                logging.info(f"Qwen-Long 匹配: {user_model_name} -> {qwen_long[0]}")
                return qwen_long[0]
        
        # 通用匹配策略
        # 1. 模糊匹配
        for available_model in available_models:
            available_lower = available_model.lower()
            
            # 如果用户输入的是部分名称，尝试匹配
            if user_model_lower in available_lower or available_lower in user_model_lower:
                logging.info(f"模糊匹配: {user_model_name} -> {available_model}")
                return available_model
        
        # 2. 清理特殊字符后比较
        for available_model in available_models:
            user_clean = re.sub(r'[:\-\./]', '', user_model_lower)
            available_clean = re.sub(r'[:\-\./]', '', available_model.lower())
            
            if user_clean in available_clean or available_clean in user_clean:
                logging.info(f"清理后匹配: {user_model_name} -> {available_model}")
                return available_model
        
        # 3. 如果没有找到匹配的，返回第一个可用模型
        if available_models:
            logging.warning(f"未找到匹配的模型，使用默认模型: {user_model_name} -> {available_models[0]}")
            return available_models[0]
        
        # 4. 如果没有任何可用模型，返回原始名称
        logging.error(f"没有可用的模型，保持原始名称: {user_model_name}")
        return user_model_name
    
    def _create_client(self, model: ModelConfig) -> Optional[AIClient]:
        """根据配置创建客户端"""
        try:
            # 根据模型类型创建对应的客户端
            if model.model_type == "qwen_long":
                return QwenLongClient(model)
            
            elif model.model_type == "lm_studio":
                # 获取可用模型列表并匹配模型名称
                try:
                    import requests
                    response = requests.get(f"{model.base_url}/models", timeout=5)
                    if response.status_code == 200:
                        models_data = response.json()
                        if models_data and models_data.get('data'):
                            available_models = [m.get('id', '') for m in models_data['data']]
                            matched_model_name = self._find_matching_model(model.model_name, available_models, model.model_type)
                            if matched_model_name != model.model_name:
                                logging.info(f"LM Studio 模型名称匹配: {model.model_name} -> {matched_model_name}")
                                # 创建临时配置对象，使用匹配后的模型名称
                                matched_model = ModelConfig(
                                    id=model.id,
                                    name=model.name,
                                    base_url=model.base_url,
                                    model_name=matched_model_name,
                                    model_type=model.model_type,
                                    api_key=model.api_key,
                                    priority=model.priority,
                                    enabled=model.enabled
                                )
                                return LMStudioClient(matched_model)
                except Exception as e:
                    logging.warning(f"获取LM Studio模型列表失败，使用原始配置: {e}")
                return LMStudioClient(model)
            
            elif model.model_type == "ollama":
                # 获取可用模型列表并匹配模型名称
                try:
                    import requests
                    response = requests.get(f"{model.base_url}/api/tags", timeout=5)
                    if response.status_code == 200:
                        models_data = response.json()
                        if models_data and models_data.get('models'):
                            available_models = [m.get('name', '') for m in models_data['models']]
                            matched_model_name = self._find_matching_model(model.model_name, available_models, model.model_type)
                            if matched_model_name != model.model_name:
                                logging.info(f"Ollama 模型名称匹配: {model.model_name} -> {matched_model_name}")
                                # 创建临时配置对象，使用匹配后的模型名称
                                matched_model = ModelConfig(
                                    id=model.id,
                                    name=model.name,
                                    base_url=model.base_url,
                                    model_name=matched_model_name,
                                    model_type=model.model_type,
                                    api_key=model.api_key,
                                    priority=model.priority,
                                    enabled=model.enabled
                                )
                                return OllamaClient(matched_model)
                except Exception as e:
                    logging.warning(f"获取Ollama模型列表失败，使用原始配置: {e}")
                return OllamaClient(model)
            
            elif model.model_type == "openai_compatible":
                # OpenAI兼容接口
                return OpenAICompatibleClient(model)
            
            else:
                logging.warning(f"未知的模型类型: {model.model_type}，尝试作为OpenAI兼容接口")
                return QwenLongClient(model)
                
        except Exception as e:
            logging.error(f"创建客户端失败 {model.name}: {e}")
            return None
    
    def chat_with_priority(self, messages: List[Dict], max_retries_per_model: int = 3) -> str:
        """按优先级与模型对话，失败时尝试下一个"""
        enabled_models = [model for model in self.models if model.enabled]
        enabled_models.sort(key=lambda x: x.priority)
        last_error = None
        
        for model in enabled_models:
            if model.id not in self.clients:
                logging.warning(f"客户端未初始化，跳过: {model.name}")
                continue
            
            try:
                logging.info(f"尝试使用模型: {model.name} (优先级: {model.priority})")
                result = self.clients[model.id].chat_with_retry(messages, max_retries_per_model)
                logging.info(f"模型 {model.name} 响应成功")
                return result
            except Exception as e:
                last_error = e
                logging.warning(f"模型 {model.name} 调用失败: {e}")
                continue
        
        # 所有模型都失败了
        error_msg = f"所有模型都调用失败，最后错误: {last_error}"
        logging.error(error_msg)
        raise AIClientError(error_msg)
    
    def test_all_connections(self) -> Dict[str, Dict[str, Any]]:
        """测试所有模型连接"""
        results = {}
        enabled_models = [model for model in self.models if model.enabled]
        
        for model in enabled_models:
            if model.id not in self.clients:
                results[model.name] = {'success': False, 'error': '客户端未初始化'}
                continue
            
            try:
                result = self.clients[model.id].test_connection()
                results[model.name] = result
            except Exception as e:
                results[model.name] = {'success': False, 'error': str(e)}
        
        return results
    
    def refresh_clients(self):
        """刷新客户端列表"""
        self._initialize_clients()
    
    def get_enabled_models(self):
        """获取启用的模型列表"""
        return [model for model in self.models if model.enabled]
    
    def get_model_info(self) -> List[Dict[str, Any]]:
        """获取模型信息"""
        info = []
        enabled_models = [model for model in self.models if model.enabled]
        
        for model in enabled_models:
            model_info = {
                'id': model.id,
                'name': model.name,
                'base_url': model.base_url,
                'model_name': model.model_name,
                'priority': model.priority,
                'enabled': model.enabled,
                'client_initialized': model.id in self.clients
            }
            info.append(model_info)
        
        return info
    
    def get_model_availability_info(self) -> List[Dict[str, Any]]:
        """获取所有模型的可用性信息"""
        info = []
        enabled_models = [model for model in self.models if model.enabled]
        
        for model in enabled_models:
            availability = self._check_model_availability(model)
            model_info = {
                'id': model.id,
                'name': model.name,
                'base_url': model.base_url,
                'model_name': model.model_name,
                'model_type': model.model_type,
                'priority': model.priority,
                'enabled': model.enabled,
                'client_initialized': model.id in self.clients,
                'available': availability['available'],
                'error': availability['error'],
                'available_models': availability['available_models'][:5],  # 只显示前5个
                'suggestions': availability['suggestions'],
                'mapped_model_name': availability.get('mapped_model_name', model.model_name)
            }
            info.append(model_info)
        
        return info
    
    def add_model(self, model: ModelConfig):
        """添加模型"""
        self.models.append(model)
        self.save_config()
        self._initialize_clients()
    
    def update_model(self, model_id: str, **kwargs):
        """更新模型配置"""
        for model in self.models:
            if model.id == model_id:
                for key, value in kwargs.items():
                    if hasattr(model, key):
                        setattr(model, key, value)
                break
        self.save_config()
        self._initialize_clients()
    
    def delete_model(self, model_id: str):
        """删除模型"""
        self.models = [model for model in self.models if model.id != model_id]
        if model_id in self.clients:
            del self.clients[model_id]
        self.save_config()
    
    def get_model_by_id(self, model_id: str) -> Optional[ModelConfig]:
        """根据ID获取模型"""
        for model in self.models:
            if model.id == model_id:
                return model
        return None
    
    def enable_model(self, model_id: str) -> bool:
        """启用模型并尝试初始化"""
        for model in self.models:
            if model.id == model_id:
                model.enabled = True
                logging.info(f"尝试启用模型: {model.name}")
                
                # 检查模型可用性
                availability = self._check_model_availability(model)
                if availability['available']:
                    # 创建客户端
                    client = self._create_client(model)
                    if client:
                        self.clients[model.id] = client
                        self.save_config()
                        logging.info(f"成功启用模型: {model.name}")
                        return True
                    else:
                        model.enabled = False
                        logging.warning(f"启用模型失败: {model.name} - 创建客户端失败")
                        return False
                else:
                    model.enabled = False
                    logging.warning(f"启用模型失败: {model.name} - {availability['error']}")
                    return False
        
        return False
    
    def get_available_models_count(self) -> int:
        """获取可用模型数量"""
        return len(self.clients)
    
    def has_available_models(self) -> bool:
        """检查是否有可用的模型"""
        return len(self.clients) > 0

# 全局AI客户端管理器实例
_ai_manager: Optional[AIClientManager] = None

def get_ai_manager() -> AIClientManager:
    """获取全局AI客户端管理器实例"""
    global _ai_manager
    if _ai_manager is None:
        _ai_manager = AIClientManager()
    return _ai_manager

def chat_with_ai(messages: List[Dict], max_retries_per_model: int = 3) -> str:
    """与AI对话的统一接口"""
    manager = get_ai_manager()
    return manager.chat_with_priority(messages, max_retries_per_model)

def test_ai_connections() -> Dict[str, Dict[str, Any]]:
    """测试所有AI连接"""
    manager = get_ai_manager()
    return manager.test_all_connections()

def refresh_ai_clients():
    """刷新AI客户端"""
    manager = get_ai_manager()
    manager.refresh_clients()

def get_model_availability_info() -> List[Dict[str, Any]]:
    """获取所有模型的可用性信息"""
    manager = get_ai_manager()
    return manager.get_model_availability_info()