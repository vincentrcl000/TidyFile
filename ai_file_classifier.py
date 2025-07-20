#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI文件内容识别模块：读取文件前500字符或用Ollama多模态模型识别内容。
"""
import os
from pathlib import Path
import ollama
import logging

class AIFileClassifier:
    def __init__(self, model_name: str = None, host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host
    
    def get_file_content_head(self, file_path: str, max_length: int = 500) -> str:
        try:
            logging.info(f"读取文件头部: {file_path}")
            print(f"[AIFileClassifier] 读取文件头部: {file_path}")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_length)
                if content and sum(1 for c in content if c.isprintable() or c.isspace()) / len(content) > 0.7:
                    return content
        except Exception as e:
            logging.warning(f"读取文件失败: {file_path}, 错误: {e}")
            print(f"[AIFileClassifier] 读取文件失败: {file_path}, 错误: {e}")
        return None
    
    def ai_classify_content(self, file_path: str, directory_json: dict) -> dict:
        logging.info(f"调用Ollama多模态模型识别: {file_path}")
        print(f"[AIFileClassifier] 调用Ollama多模态模型识别: {file_path}")
        client = ollama.Client(host=self.host)
        dir_names = self._flatten_dir_names(directory_json)
        prompt = f"请阅读文件内容，判断最适合归类到以下哪个目录：{dir_names}。只返回最优目录名。/no_think"
        
        # 在输入内容尾部添加/no_think标签
        final_prompt = prompt
        
        # 同时使用三种策略抑制思考过程
        generate_params = {
            'model': self.model_name,
            'prompt': final_prompt,
            'files': [file_path],
            'options': {'enable_thinking': False}  # 策略2：传递enable_thinking参数
        }
        
        response = client.generate(**generate_params)
        logging.info(f"Ollama返回: {response['response'].strip()}")
        print(f"[AIFileClassifier] Ollama返回: {response['response'].strip()}")
        return {'best_match': response['response'].strip()}
    
    def get_best_match(self, file_path: str, directory_json: dict) -> dict:
        content = self.get_file_content_head(file_path)
        if content:
            dir_names = self._flatten_dir_names(directory_json)
            scores = [(name, content.count(name)) for name in dir_names]
            scores.sort(key=lambda x: -x[1])
            best = scores[0][0] if scores and scores[0][1] > 0 else None
            logging.info(f"文本匹配结果: {file_path} -> {best}")
            print(f"[AIFileClassifier] 文本匹配结果: {file_path} -> {best}")
            return {'best_match': best, 'scores': scores}
        else:
            return self.ai_classify_content(file_path, directory_json)
    
    def _flatten_dir_names(self, directory_json: dict) -> list:
        names = [directory_json['name']]
        for child in directory_json.get('children', []):
            names.extend(self._flatten_dir_names(child))
        return names 