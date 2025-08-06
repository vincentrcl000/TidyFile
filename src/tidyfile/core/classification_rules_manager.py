 #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分类规则管理器
用于管理用户自定义的文件夹分类规则
"""
import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

class ClassificationRulesManager:
    """分类规则管理器"""
    
    def __init__(self, rules_file: str = None):
        """
        初始化分类规则管理器
        
        Args:
            rules_file: 规则文件路径
        """
        # 使用新的路径管理
        try:
            from tidyfile.utils.app_paths import get_app_paths
            app_paths = get_app_paths()
            self.rules_file = str(app_paths.classification_rules_file)
        except ImportError:
            # 兼容旧版本
            self.rules_file = rules_file or "classification_rules.json"
        
        self.rules = {}
        self.load_rules()
        
    def load_rules(self) -> None:
        """加载分类规则"""
        try:
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    self.rules = json.load(f)
                logging.info(f"成功加载分类规则，共 {len(self.rules)} 条规则")
            else:
                self.rules = {}
                logging.info("分类规则文件不存在，将创建新文件")
        except Exception as e:
            logging.error(f"加载分类规则失败: {e}")
            self.rules = {}
    
    def save_rules(self) -> None:
        """保存分类规则"""
        try:
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
            logging.info(f"成功保存分类规则，共 {len(self.rules)} 条规则")
        except Exception as e:
            logging.error(f"保存分类规则失败: {e}")
    
    def add_rule(self, folder_name: str, description: str, keywords: List[str] = None) -> bool:
        """
        添加分类规则
        
        Args:
            folder_name: 文件夹名称
            description: 存放内容说明
            keywords: 关键词列表（可选）
            
        Returns:
            bool: 是否添加成功
        """
        try:
            if not folder_name or not description:
                logging.warning("文件夹名称和说明不能为空")
                return False
            
            # 清理文件夹名称（移除路径分隔符等）
            clean_folder_name = self._clean_folder_name(folder_name)
            
            self.rules[clean_folder_name] = {
                "description": description,
                "keywords": keywords or [],
                "created_time": self._get_current_time(),
                "updated_time": self._get_current_time()
            }
            
            self.save_rules()
            logging.info(f"成功添加分类规则: {clean_folder_name}")
            return True
            
        except Exception as e:
            logging.error(f"添加分类规则失败: {e}")
            return False
    
    def update_rule(self, folder_name: str, description: str = None, keywords: List[str] = None) -> bool:
        """
        更新分类规则
        
        Args:
            folder_name: 文件夹名称
            description: 新的存放内容说明
            keywords: 新的关键词列表
            
        Returns:
            bool: 是否更新成功
        """
        try:
            clean_folder_name = self._clean_folder_name(folder_name)
            
            if clean_folder_name not in self.rules:
                logging.warning(f"分类规则不存在: {clean_folder_name}")
                return False
            
            if description is not None:
                self.rules[clean_folder_name]["description"] = description
            
            if keywords is not None:
                self.rules[clean_folder_name]["keywords"] = keywords
            
            self.rules[clean_folder_name]["updated_time"] = self._get_current_time()
            
            self.save_rules()
            logging.info(f"成功更新分类规则: {clean_folder_name}")
            return True
            
        except Exception as e:
            logging.error(f"更新分类规则失败: {e}")
            return False
    
    def delete_rule(self, folder_name: str) -> bool:
        """
        删除分类规则
        
        Args:
            folder_name: 文件夹名称
            
        Returns:
            bool: 是否删除成功
        """
        try:
            clean_folder_name = self._clean_folder_name(folder_name)
            
            if clean_folder_name not in self.rules:
                logging.warning(f"分类规则不存在: {clean_folder_name}")
                return False
            
            del self.rules[clean_folder_name]
            self.save_rules()
            logging.info(f"成功删除分类规则: {clean_folder_name}")
            return True
            
        except Exception as e:
            logging.error(f"删除分类规则失败: {e}")
            return False
    
    def get_rule(self, folder_name: str) -> Optional[Dict]:
        """
        获取分类规则
        
        Args:
            folder_name: 文件夹名称
            
        Returns:
            Dict: 分类规则，如果不存在返回None
        """
        clean_folder_name = self._clean_folder_name(folder_name)
        return self.rules.get(clean_folder_name)
    
    def get_all_rules(self) -> Dict:
        """
        获取所有分类规则
        
        Returns:
            Dict: 所有分类规则
        """
        return self.rules.copy()
    
    def find_matching_folders(self, content: str, file_name: str, available_folders: List[str]) -> List[Tuple[str, float]]:
        """
        根据内容和文件名找到匹配的文件夹
        
        Args:
            content: 文件内容
            file_name: 文件名
            available_folders: 可用的文件夹列表
            
        Returns:
            List[Tuple[str, float]]: 匹配的文件夹和匹配度
        """
        matches = []
        
        # 组合内容和文件名用于匹配
        search_text = f"{content} {file_name}".lower()
        
        for folder in available_folders:
            clean_folder_name = self._clean_folder_name(folder)
            rule = self.rules.get(clean_folder_name)
            
            if rule:
                # 计算匹配度
                match_score = self._calculate_match_score(search_text, rule)
                if match_score > 0:
                    matches.append((folder, match_score))
        
        # 按匹配度排序
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def _calculate_match_score(self, search_text: str, rule: Dict) -> float:
        """
        计算匹配度
        
        Args:
            search_text: 搜索文本
            rule: 分类规则
            
        Returns:
            float: 匹配度（0-1）
        """
        score = 0.0
        
        # 基于描述的匹配
        description = rule.get("description", "").lower()
        if description:
            # 使用序列匹配器计算相似度
            similarity = SequenceMatcher(None, search_text, description).ratio()
            score += similarity * 0.6  # 描述匹配权重60%
        
        # 基于关键词的匹配
        keywords = rule.get("keywords", [])
        if keywords:
            keyword_matches = 0
            for keyword in keywords:
                if keyword.lower() in search_text:
                    keyword_matches += 1
            
            if keyword_matches > 0:
                keyword_score = keyword_matches / len(keywords)
                score += keyword_score * 0.4  # 关键词匹配权重40%
        
        return min(score, 1.0)
    
    def _clean_folder_name(self, folder_name: str) -> str:
        """
        清理文件夹名称
        
        Args:
            folder_name: 原始文件夹名称
            
        Returns:
            str: 清理后的文件夹名称
        """
        # 移除路径分隔符，只保留文件夹名
        return Path(folder_name).name
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_rules_for_prompt(self, available_folders: List[str]) -> str:
        """
        获取用于AI提示词的规则说明
        
        Args:
            available_folders: 可用的文件夹列表
            
        Returns:
            str: 格式化的规则说明
        """
        if not self.rules:
            return ""
        
        rules_text = []
        rules_text.append("用户自定义分类规则：")
        
        for folder in available_folders:
            clean_folder_name = self._clean_folder_name(folder)
            rule = self.rules.get(clean_folder_name)
            
            if rule:
                description = rule.get("description", "")
                keywords = rule.get("keywords", [])
                
                rule_line = f"- {folder}: {description}"
                if keywords:
                    rule_line += f" (关键词: {', '.join(keywords)})"
                
                rules_text.append(rule_line)
        
        return "\n".join(rules_text) if rules_text else ""
    
    def export_rules(self, export_file: str) -> bool:
        """
        导出分类规则
        
        Args:
            export_file: 导出文件路径
            
        Returns:
            bool: 是否导出成功
        """
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
            logging.info(f"成功导出分类规则到: {export_file}")
            return True
        except Exception as e:
            logging.error(f"导出分类规则失败: {e}")
            return False
    
    def import_rules(self, import_file: str, merge: bool = True) -> bool:
        """
        导入分类规则
        
        Args:
            import_file: 导入文件路径
            merge: 是否合并现有规则
            
        Returns:
            bool: 是否导入成功
        """
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                imported_rules = json.load(f)
            
            if merge:
                self.rules.update(imported_rules)
            else:
                self.rules = imported_rules
            
            self.save_rules()
            logging.info(f"成功导入分类规则，共 {len(imported_rules)} 条规则")
            return True
        except Exception as e:
            logging.error(f"导入分类规则失败: {e}")
            return False