#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国际化管理模块

本模块提供多语言支持功能，包括：
1. 语言文件加载和管理
2. 语言切换功能
3. 语言检测和回退机制
4. 动态文本翻译

作者: AI Assistant
创建时间: 2025-08-05
"""

import json
import locale
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from tidyfile.utils.app_paths import get_app_paths

logger = logging.getLogger(__name__)


class I18nManager:
    """国际化管理器"""

    def __init__(self, default_language: str = "zh-CN"):
        """
        初始化国际化管理器

        Args:
            default_language: 默认语言代码
        """
        self.default_language = default_language
        self.current_language = default_language
        self.translations = {}
        self.app_paths = get_app_paths()
        self._load_language_files()

    def _load_language_files(self):
        """加载语言文件"""
        locales_dir = self.app_paths.user_data_dir / "locales"
        
        # 确保语言文件目录存在
        locales_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载所有语言文件
        for lang_file in locales_dir.glob("*.json"):
            lang_code = lang_file.stem
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
                logger.info(f"加载语言文件: {lang_code}")
            except Exception as e:
                logger.error(f"加载语言文件失败 {lang_code}: {e}")
        
        # 如果没有找到任何语言文件，创建默认语言文件
        if not self.translations:
            logger.warning("没有找到语言文件，创建默认语言文件")
            self._create_default_language_files(locales_dir)
            # 重新加载创建的语言文件
            for lang_file in locales_dir.glob("*.json"):
                lang_code = lang_file.stem
                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                    logger.info(f"加载默认语言文件: {lang_code}")
                except Exception as e:
                    logger.error(f"加载默认语言文件失败 {lang_code}: {e}")

    def _create_default_language_files(self, locales_dir: Path):
        """创建默认语言文件"""
        # 中文语言文件
        zh_cn_file = locales_dir / "zh-CN.json"
        if not zh_cn_file.exists():
            zh_cn_translations = {
                "app": {
                    "title": "智能文件管理系统",
                    "version": "版本",
                    "settings": "设置",
                    "about": "关于",
                    "exit": "退出",
                    "operation_log": "操作日志",
                    "clear_log": "清空日志",
                    "log_level": "日志级别:",
                    "startup_message": "程序启动完成，请选择文件目录开始整理",
                    "file_reader": "文件解读",
                    "article_reader": "文章阅读助手",
                    "ai_classifier": "智能分类",
                    "tools": "工具",
                    "weixin_manager": "微信文章管理",
                    "system_tools": "系统工具",
                    "tag_optimizer": "标签优化工具",
                    "tag_manager": "标签管理器",
                    "transfer_logs": "转移日志管理",
                    "duplicate_remover": "重复文件清理",
                    "classification_rules": "分类规则管理",
                    "ai_model_config": "AI模型配置",
                    "multi_task_reader": "多任务文件解读",
                    "multi_process_reader": "多进程文件解读",
                    "directory_organizer": "文件目录智能整理",
                    "language_settings": "语言设置",
                    "ai_classifier_init_complete": "智能文件分类器初始化完成",
                    "file_organizer_init_complete": "文件整理器初始化完成"
                },
                "file_organizer": {
                    "title": "文件整理器",
                    "select_folder": "选择文件夹",
                    "organize_files": "整理文件",
                    "progress": "进度",
                    "completed": "完成",
                    "error": "错误",
                    "select_source_directory": "待整理文件目录:",
                    "select_target_directory": "目标分类目录:",
                    "browse": "浏览",
                    "summary_length": "摘要长度:",
                    "content_truncate": "内容截取:",
                    "start_ai_organize": "开始AI智能整理",
                    "organizing_files": "正在整理文件...",
                    "organize_completed": "整理完成",
                    "organize_failed": "整理失败",
                    "please_select_directories": "请选择源目录和目标目录",
                    "characters": "字符",
                    "full_text": "全文"
                },
                "ai_classifier": {
                    "title": "AI智能分类",
                    "description": "使用 AI 智能分析文件内容，自动将文件分类到合适的文件夹中",
                    "source_directory": "待整理文件目录:",
                    "target_directory": "目标分类目录:",
                    "browse": "浏览",
                    "ai_params": "AI参数设置",
                    "summary_length": "摘要长度:",
                    "content_truncate": "内容截取:",
                    "characters": "字符",
                    "full_text": "全文",
                    "start_ai_organize": "开始AI智能整理",
                    "organizing_files": "正在整理文件...",
                    "organize_completed": "整理完成",
                    "organize_failed": "整理失败",
                    "please_select_directories": "请选择源目录和目标目录",
                    "confirm_organize": "确认整理",
                    "confirm_message": "即将开始AI智能整理:\n\n源目录: {source}\n目标目录: {target}\n\n确定要继续吗？",
                    "operation_cancelled": "AI智能整理操作已取消",
                    "error_no_directories": "请先选择源目录和目标目录",
                    "organize_failed_no_dirs": "AI智能整理失败：未选择源目录或目标目录"
                },
                "duplicate_remover": {
                    "title": "重复文件清理",
                    "scan_duplicates": "扫描重复文件",
                    "remove_duplicates": "删除重复文件",
                    "duplicate_count": "重复文件数量",
                    "space_saved": "节省空间"
                },
                "weixin_manager": {
                    "title": "微信文章管理",
                    "import_articles": "导入文章",
                    "export_articles": "导出文章",
                    "article_count": "文章数量",
                    "generate_summary": "生成摘要",
                    "favorites_organize": "收藏文章整理",
                    "account": "收藏账号:",
                    "start_date": "起始日期:",
                    "end_date": "结束日期:",
                    "summary_length": "摘要长度:",
                    "characters": "字符",
                    "backup_articles": "收藏文章备份",
                    "analyze_backup": "备份文章解读",
                    "input_error": "输入错误",
                    "please_enter_account": "请输入收藏账号",
                    "please_enter_dates": "请输入起始和结束日期",
                    "date_format_error": "日期格式错误，请使用 YYYY-MM-DD 格式",
                    "start_date_after_end": "起始日期不能晚于结束日期",
                    "backup_completed": "备份完成",
                    "backup_failed": "备份失败",
                    "analyze_completed": "解读完成",
                    "analyze_failed": "解读失败"
                },
                "file_reader": {
                    "title": "文件解读",
                    "description": "选择文件夹，批量解读其中的所有文档，生成摘要并保存到AI结果文件",
                    "select_folder": "选择文件夹:",
                    "browse": "浏览",
                    "folder_scan_failed": "文件夹扫描失败",
                    "summary_params": "摘要参数设置",
                    "summary_length": "文章摘要长度:",
                    "characters_100": "100字",
                    "characters_500": "500字",
                    "characters_200": "200字符",
                    "start_batch_reading": "开始批量解读",
                    "reading_documents": "正在解读文档...",
                    "batch_reading_completed": "批量解读完成",
                    "reading_failed": "解读失败",
                    "please_select_folder": "请选择要解读的文件夹"
                },
                "article_reader": {
                    "title": "文章阅读助手",
                    "description": "启动文章阅读助手服务器，在浏览器中查看和管理AI分析结果",
                    "features": "功能特性",
                    "feature_view_results": "• 查看AI分析结果和文件摘要",
                    "feature_open_files": "• 直接打开文件进行查看",
                    "feature_refresh_records": "• 重复解读后点击刷新删除重复记录",
                    "feature_web_interface": "• 友好的Web界面",
                    "start_article_reader": "启动文章阅读助手",
                    "usage_instructions": "使用说明",
                    "instruction_1": "1. 点击上方按钮启动文章阅读助手",
                    "instruction_2": "2. 服务器将在新的控制台窗口中运行",
                    "instruction_3": "3. 浏览器会自动打开AI结果查看页面",
                    "instruction_4": "4. 局域网内其他设备可通过显示的IP地址访问",
                    "instruction_5": "5. 使用完毕后，直接关闭浏览器即可自动停止服务器",
                    "article_reader_started": "文章阅读助手已启动",
                    "local_access": "本机访问",
                    "lan_access": "局域网访问",
                    "copy": "复制",
                    "copied": "已复制",
                    "open_local": "本机打开",
                    "open_lan": "局域网打开",
                    "close": "关闭",
                    "server_running": "服务器已在运行",
                    "startup_success": "启动成功",
                    "server_starting": "启动文章阅读助手服务器...",
                    "server_started": "已启动文章阅读助手服务器",
                    "server_detected": "检测到已有服务器运行，请直接在浏览器访问",
                    "folder_scan_failed": "文件夹扫描失败"
                },
                "tag_manager": {
                    "title": "标签管理器",
                    "description": "从ai_organize_result.json中提取所有链式标签的第一个标签段，支持批量删除",
                    "tag_list": "一级标签列表",
                    "loading": "正在加载...",
                    "select_all": "全选",
                    "deselect_all": "取消全选",
                    "refresh": "刷新",
                    "operation_preview": "操作预览",
                    "select_tags_to_delete": "选中要删除的标签，点击下方按钮执行操作",
                    "preview_deletion": "预览删除效果",
                    "execute_deletion": "执行删除",
                    "backup_file": "备份原文件"
                },
                "transfer_logs": {
                    "title": "转移日志管理",
                    "log_list": "转移日志列表",
                    "view_details": "查看详情",
                    "restore_files": "恢复文件",
                    "refresh": "刷新",
                    "clean_old_logs": "清理旧日志",
                    "close": "关闭",
                    "basic_info": "基本信息",
                    "file_list": "文件列表",
                    "source_file": "源文件",
                    "target_file": "目标文件",
                    "status": "状态",
                    "file_restore": "文件恢复操作",
                    "operation_mode": "操作模式",
                    "preview_mode": "预览模式（仅显示将要恢复的文件，不实际执行）",
                    "execute_mode": "执行模式（实际恢复文件）",
                    "confirm": "确定",
                    "delete_source_files": "删除源文件"
                },
                "directory_organizer": {
                    "title": "文件目录智能整理",
                    "description": "选择要整理的目录，AI将智能分析并推荐优化的目录结构",
                    "select_directories": "选择要整理的目录",
                    "refresh_system_directories": "刷新系统目录",
                    "selected_directories": "已选择的目录",
                    "ai_recommendation": "AI推荐结果",
                    "new_directory_location": "新建目录位置:",
                    "select": "选择",
                    "remove_selected": "移除选中",
                    "clear_list": "清空列表",
                    "smart_recommendation": "智能推荐",
                    "re_recommendation": "重新推荐",
                    "use_this_recommendation": "使用此推荐目录",
                    "close": "关闭",
                    "start_restore": "开始恢复",
                    "cancel": "取消",
                    "confirm": "确定",
                    "delete_source_files": "删除源文件"
                },
                "tools": {
                    "title": "系统工具",
                    "transfer_logs": "转移日志管理",
                    "duplicate_remover": "重复文件清理",
                    "classification_rules": "分类规则管理",
                    "ai_model_config": "AI模型配置",
                    "tag_manager": "标签管理器",
                    "tag_optimizer": "标签优化工具",
                    "multi_task_reader": "多任务文件解读",
                    "multi_process_reader": "多进程文件解读",
                    "directory_organizer": "文件目录智能整理",
                    "language_settings": "语言设置",
                    "language_settings_desc": "设置应用程序界面语言，支持中文和英文",
                    "duplicate_remover_desc": "扫描并删除系统中的重复文件，节省存储空间",
                    "classification_rules_desc": "管理文件分类规则，自定义文件整理策略",
                    "ai_model_config_desc": "配置和管理AI模型参数，优化智能分类效果",
                    "tag_manager_desc": "管理文件标签，批量删除和整理标签体系",
                    "tag_optimizer_desc": "智能优化标签体系，包括标签分析、AI推荐、格式化等功能",
                    "multi_task_reader_desc": "支持同时启动多个文件解读任务，每个任务独立处理不同的文件夹",
                    "multi_process_reader_desc": "支持多任务多进程并行处理，充分利用大模型的并行处理能力",
                    "transfer_logs_desc": "查看文件操作历史记录，支持操作回滚"
                },
                "tag_optimizer": {
                    "title": "标签优化工具",
                    "description": "智能优化ai_organize_result.json中的标签体系，包括分析、AI推荐、格式化等功能",
                    "function_selection": "功能选择",
                    "current_tag_analysis": "当前标签分析",
                    "current_tag_analysis_desc": "扫描并分析当前链式标签情况，显示统计信息",
                    "smart_tags": "智能标签",
                    "smart_tags_desc": "针对空标签、没有标签字段的记录使用AI推荐三级标签（增强版）",
                    "tag_formatting": "标签格式化",
                    "tag_formatting_desc": "格式化链式标签，清理特殊字符和多余空格（推荐在进行迁移、文章解读后使用）",
                    "operation_result": "操作结果",
                    "clear_result": "清空结果",
                    "save_result": "保存结果",
                    "refresh_data": "刷新数据"
                },
                "settings": {
                    "title": "应用设置",
                    "language": "语言",
                    "theme": "主题",
                    "ai_models": "AI模型",
                    "classification_rules": "分类规则",
                    "save": "保存",
                    "cancel": "取消",
                    "reset": "重置",
                    "language_settings": "语言设置",
                    "current_language": "当前语言",
                    "select_language": "选择语言",
                    "apply": "应用",
                    "language_changed": "语言设置已更改",
                    "restart_required": "需要重启",
                    "restart_message": "语言设置已保存，需要重启应用程序才能生效。是否现在重启？",
                    "save_settings_failed": "保存设置失败",
                    "language_change_failed": "语言切换失败"
                },
                "messages": {
                    "success": "操作成功",
                    "error": "操作失败",
                    "warning": "警告",
                    "info": "信息",
                    "confirm": "确认",
                    "cancel": "取消",
                    "yes": "是",
                    "no": "否",
                    "no_content_to_save": "没有内容可保存",
                    "result_saved_to": "结果已保存到: {filename}",
                    "save_failed": "保存失败: {e}",
                    "file_not_exists": "文件 {file_path} 不存在",
                    "load_tag_data_failed": "加载标签数据失败: {e}",
                    "please_select_tags_to_delete": "请先选择要删除的标签",
                    "delete_operation_completed": "删除操作完成！\n修改了 {count} 条记录",
                    "execute_delete_failed": "执行删除操作失败: {e}",
                    "file_backed_up_to": "文件已备份到：\n{backup_path}",
                    "backup_failed": "备份文件失败: {e}",
                    "file_organizer_init_failed": "文件整理器初始化失败: {e}",
                    "please_select_folder_to_read": "请先选择要解读的文件夹",
                    "selected_folder_not_exists": "选择的文件夹不存在",
                    "startup_script_not_found": "找不到启动脚本: {script}",
                    "start_article_reader_failed": "启动文章阅读助手失败: {e}",
                    "batch_reading_completed": "批量解读完成！\n\n成功解读: {success} 个\n解读失败: {failed} 个\n\n结果已保存到: ai_organize_result.json",
                    "batch_document_reading_failed": "批量文档解读失败: {error}",
                    "please_select_directories": "请先选择源目录和目标目录",
                    "ai_organize_failed": "AI整理失败: {error}",
                    "delete_completed": "删除完成",
                    "delete_failed": "删除失败",
                    "delete_source_files_error": "删除源文件时出错: {error}",
                    "transfer_logs_not_enabled": "转移日志功能未启用",
                    "show_transfer_logs_failed": "显示转移日志失败: {error}",
                    "show_duplicate_remover_failed": "显示重复文件删除对话框失败: {e}",
                    "open_classification_rules_failed": "打开分类规则管理器失败: {e}",
                    "show_ai_model_config_failed": "显示AI模型配置失败: {e}",
                    "open_tag_manager_failed": "打开标签管理器失败: {e}",
                    "open_tag_optimizer_failed": "打开标签优化工具失败: {e}",
                    "start_multi_task_reader_failed": "启动多任务文件解读管理器失败: {e}",
                    "start_multi_process_reader_failed": "启动高并发文件解读管理器失败: {e}",
                    "i18n_module_not_loaded": "国际化模块未加载，无法使用语言设置功能",
                    "refresh_drives_failed": "刷新盘符失败: {e}",
                    "please_select_directories_to_organize": "请先选择要整理的目录",
                    "please_select_new_directory_location": "请先选择新建目录的位置",
                    "please_generate_ai_recommendation": "请先生成AI推荐",
                    "directory_structure_created": "目录结构创建完成！\n\n请使用智能分类或文件分类功能将原文件迁移到新的目录中。",
                    "create_directory_structure_failed": "创建目录结构失败: {e}",
                    "please_select_log_record": "请先选择一个日志记录",
                    "please_select_valid_log_record": "请先选择一个有效的日志记录",
                    "cannot_load_log_file": "无法加载日志文件: {filename}",
                    "show_log_details_failed": "显示日志详情失败: {e}",
                    "log_file_not_exists": "日志文件不存在: {filename}",
                    "show_restore_dialog_failed": "显示恢复对话框失败: {e}"
                },
                "errors": {
                    "file_not_found": "文件未找到",
                    "permission_denied": "权限不足",
                    "invalid_config": "配置无效",
                    "network_error": "网络错误",
                    "ai_model_error": "AI模型错误"
                }
            }
            self._save_language_file(zh_cn_file, zh_cn_translations)

        # 英文语言文件
        en_us_file = locales_dir / "en-US.json"
        if not en_us_file.exists():
            en_us_translations = {
                "app": {
                    "title": "Smart File Management System",
                    "version": "Version",
                    "settings": "Settings",
                    "about": "About",
                    "exit": "Exit",
                    "operation_log": "Operation Log",
                    "clear_log": "Clear Log",
                    "log_level": "Log Level:",
                    "startup_message": "Program started successfully, please select a file directory to begin organization",
                    "file_reader": "File Reader",
                    "article_reader": "Article Reader",
                    "ai_classifier": "AI Classifier",
                    "tools": "Tools",
                    "weixin_manager": "WeChat Manager",
                    "system_tools": "System Tools",
                    "tag_optimizer": "Tag Optimizer",
                    "tag_manager": "Tag Manager",
                    "transfer_logs": "Transfer Logs",
                    "duplicate_remover": "Duplicate Remover",
                    "classification_rules": "Classification Rules",
                    "ai_model_config": "AI Model Config",
                    "multi_task_reader": "Multi-Task Reader",
                    "multi_process_reader": "Multi-Process Reader",
                    "directory_organizer": "Directory Organizer",
                    "language_settings": "Language Settings",
                    "ai_classifier_init_complete": "AI classifier initialization complete",
                    "file_organizer_init_complete": "File organizer initialization complete"
                },
                "file_organizer": {
                    "title": "File Organizer",
                    "select_folder": "Select Folder",
                    "organize_files": "Organize Files",
                    "progress": "Progress",
                    "completed": "Completed",
                    "error": "Error",
                    "select_source_directory": "Source Directory:",
                    "select_target_directory": "Target Directory:",
                    "browse": "Browse",
                    "summary_length": "Summary Length:",
                    "content_truncate": "Content Truncate:",
                    "start_ai_organize": "Start AI Organization",
                    "organizing_files": "Organizing files...",
                    "organize_completed": "Organization completed",
                    "organize_failed": "Organization failed",
                    "please_select_directories": "Please select source and target directories",
                    "characters": "characters",
                    "full_text": "Full text"
                },
                "ai_classifier": {
                    "title": "AI Smart Classifier",
                    "description": "Use AI to intelligently analyze file content and automatically classify files into appropriate folders",
                    "source_directory": "Source Directory:",
                    "target_directory": "Target Directory:",
                    "browse": "Browse",
                    "ai_params": "AI Parameters",
                    "summary_length": "Summary Length:",
                    "content_truncate": "Content Truncate:",
                    "characters": "characters",
                    "full_text": "Full text",
                    "start_ai_organize": "Start AI Organization",
                    "organizing_files": "Organizing files...",
                    "organize_completed": "Organization completed",
                    "organize_failed": "Organization failed",
                    "please_select_directories": "Please select source and target directories",
                    "confirm_organize": "Confirm Organization",
                    "confirm_message": "About to start AI intelligent organization:\n\nSource directory: {source}\nTarget directory: {target}\n\nAre you sure you want to continue?",
                    "operation_cancelled": "AI organization operation cancelled",
                    "error_no_directories": "Please select source and target directories first",
                    "organize_failed_no_dirs": "AI organization failed: source or target directory not selected"
                },
                "duplicate_remover": {
                    "title": "Duplicate File Remover",
                    "scan_duplicates": "Scan Duplicates",
                    "remove_duplicates": "Remove Duplicates",
                    "duplicate_count": "Duplicate Count",
                    "space_saved": "Space Saved"
                },
                "weixin_manager": {
                    "title": "WeChat Article Manager",
                    "import_articles": "Import Articles",
                    "export_articles": "Export Articles",
                    "article_count": "Article Count",
                    "generate_summary": "Generate Summary",
                    "favorites_organize": "Favorites Organize",
                    "account": "Account:",
                    "start_date": "Start Date:",
                    "end_date": "End Date:",
                    "summary_length": "Summary Length:",
                    "characters": "characters",
                    "backup_articles": "Backup Articles",
                    "analyze_backup": "Analyze Backup",
                    "input_error": "Input Error",
                    "please_enter_account": "Please enter account",
                    "please_enter_dates": "Please enter start and end dates",
                    "date_format_error": "Date format error, please use YYYY-MM-DD format",
                    "start_date_after_end": "Start date cannot be later than end date",
                    "backup_completed": "Backup completed",
                    "backup_failed": "Backup failed",
                    "analyze_completed": "Analysis completed",
                    "analyze_failed": "Analysis failed"
                },
                "file_reader": {
                    "title": "File Reader",
                    "description": "Select a folder to batch read all documents, generate summaries and save to AI result files",
                    "select_folder": "Select Folder:",
                    "browse": "Browse",
                    "folder_scan_failed": "Folder scan failed",
                    "summary_params": "Summary Parameters",
                    "summary_length": "Article Summary Length:",
                    "characters_100": "100 chars",
                    "characters_500": "500 chars",
                    "characters_200": "200 chars",
                    "start_batch_reading": "Start Batch Reading",
                    "reading_documents": "Reading documents...",
                    "batch_reading_completed": "Batch reading completed",
                    "reading_failed": "Reading failed",
                    "please_select_folder": "Please select a folder to read"
                },
                "article_reader": {
                    "title": "Article Reader",
                    "description": "Start the article reader server to view and manage AI analysis results in browser",
                    "features": "Features",
                    "feature_view_results": "• View AI analysis results and file summaries",
                    "feature_open_files": "• Open files directly for viewing",
                    "feature_refresh_records": "• Click refresh after duplicate reading to remove duplicate records",
                    "feature_web_interface": "• Friendly web interface",
                    "start_article_reader": "Start Article Reader",
                    "usage_instructions": "Usage Instructions",
                    "instruction_1": "1. Click the button above to start the article reader",
                    "instruction_2": "2. The server will run in a new console window",
                    "instruction_3": "3. The browser will automatically open the AI results viewing page",
                    "instruction_4": "4. Other devices on the local network can access via the displayed IP address",
                    "instruction_5": "5. After use, simply close the browser to automatically stop the server",
                    "article_reader_started": "Article Reader Started",
                    "local_access": "Local Access",
                    "lan_access": "LAN Access",
                    "copy": "Copy",
                    "copied": "Copied",
                    "open_local": "Open Local",
                    "open_lan": "Open LAN",
                    "close": "Close",
                    "server_running": "Server is running",
                    "startup_success": "Startup successful",
                    "server_starting": "Starting article reader server...",
                    "server_started": "Article reader server started",
                    "server_detected": "Detected existing server running, please access directly in browser",
                    "folder_scan_failed": "Folder scan failed"
                },
                "tag_manager": {
                    "title": "Tag Manager",
                    "description": "Extract the first tag segment from all chain tags in ai_organize_result.json, supports batch deletion",
                    "tag_list": "Primary Tag List",
                    "loading": "Loading...",
                    "select_all": "Select All",
                    "deselect_all": "Deselect All",
                    "refresh": "Refresh",
                    "operation_preview": "Operation Preview",
                    "select_tags_to_delete": "Select tags to delete, click buttons below to execute operations",
                    "preview_deletion": "Preview Deletion",
                    "execute_deletion": "Execute Deletion",
                    "backup_file": "Backup File"
                },
                "transfer_logs": {
                    "title": "Transfer Logs",
                    "log_list": "Transfer Log List",
                    "view_details": "View Details",
                    "restore_files": "Restore Files",
                    "refresh": "Refresh",
                    "clean_old_logs": "Clean Old Logs",
                    "close": "Close",
                    "basic_info": "Basic Info",
                    "file_list": "File List",
                    "source_file": "Source File",
                    "target_file": "Target File",
                    "status": "Status",
                    "file_restore": "File Restore",
                    "operation_mode": "Operation Mode",
                    "preview_mode": "Preview Mode (only show files to be restored, no actual execution)",
                    "execute_mode": "Execute Mode (actually restore files)",
                    "confirm": "Confirm",
                    "delete_source_files": "Delete Source Files"
                },
                "directory_organizer": {
                    "title": "Directory Organizer",
                    "description": "Select directories to organize, AI will intelligently analyze and recommend optimized directory structure",
                    "select_directories": "Select Directories to Organize",
                    "refresh_system_directories": "Refresh System Directories",
                    "selected_directories": "Selected Directories",
                    "ai_recommendation": "AI Recommendation",
                    "new_directory_location": "New Directory Location:",
                    "select": "Select",
                    "remove_selected": "Remove Selected",
                    "clear_list": "Clear List",
                    "smart_recommendation": "Smart Recommendation",
                    "re_recommendation": "Re-recommendation",
                    "use_this_recommendation": "Use This Recommendation",
                    "close": "Close",
                    "start_restore": "Start Restore",
                    "cancel": "Cancel",
                    "confirm": "Confirm",
                    "delete_source_files": "Delete Source Files"
                },
                "tools": {
                    "title": "System Tools",
                    "transfer_logs": "Transfer Logs",
                    "duplicate_remover": "Duplicate Remover",
                    "classification_rules": "Classification Rules",
                    "ai_model_config": "AI Model Config",
                    "tag_manager": "Tag Manager",
                    "tag_optimizer": "Tag Optimizer",
                    "multi_task_reader": "Multi-Task Reader",
                    "multi_process_reader": "Multi-Process Reader",
                    "directory_organizer": "Directory Organizer",
                    "language_settings": "Language Settings",
                    "language_settings_desc": "Set application interface language, supports Chinese and English",
                    "duplicate_remover_desc": "Scan and delete duplicate files in the system, save storage space",
                    "classification_rules_desc": "Manage file classification rules, customize file organization strategies",
                    "ai_model_config_desc": "Configure and manage AI model parameters, optimize intelligent classification effects",
                    "tag_manager_desc": "Manage file tags, batch delete and organize tag system",
                    "tag_optimizer_desc": "Intelligently optimize tag system, including tag analysis, AI recommendation, formatting and other functions",
                    "multi_task_reader_desc": "Supports launching multiple file interpretation tasks simultaneously, each task independently processes different folders",
                    "multi_process_reader_desc": "Supports multi-task multi-process parallel processing, fully utilizing the parallel processing capabilities of large models",
                    "transfer_logs_desc": "View file operation history records, support operation rollback"
                },
                "tag_optimizer": {
                    "title": "Tag Optimizer",
                    "description": "Intelligently optimize the tag system in ai_organize_result.json, including analysis, AI recommendation, formatting and other functions",
                    "function_selection": "Function Selection",
                    "current_tag_analysis": "Current Tag Analysis",
                    "current_tag_analysis_desc": "Scan and analyze current chain tag situation, display statistics",
                    "smart_tags": "Smart Tags",
                    "smart_tags_desc": "Use AI to recommend three-level tags for records with empty tags or no tag fields (enhanced version)",
                    "tag_formatting": "Tag Formatting",
                    "tag_formatting_desc": "Format chain tags, clean special characters and extra spaces (recommended after migration and article reading)",
                    "operation_result": "Operation Result",
                    "clear_result": "Clear Result",
                    "save_result": "Save Result",
                    "refresh_data": "Refresh Data"
                },
                "settings": {
                    "title": "Application Settings",
                    "language": "Language",
                    "theme": "Theme",
                    "ai_models": "AI Models",
                    "classification_rules": "Classification Rules",
                    "save": "Save",
                    "cancel": "Cancel",
                    "reset": "Reset",
                    "language_settings": "Language Settings",
                    "current_language": "Current Language",
                    "select_language": "Select Language",
                    "apply": "Apply",
                    "language_changed": "Language settings changed",
                    "restart_required": "Restart Required",
                    "restart_message": "Language settings have been saved. Restart the application to take effect. Restart now?",
                    "save_settings_failed": "Failed to save settings",
                    "language_change_failed": "Failed to change language"
                },
                "messages": {
                    "success": "Operation Successful",
                    "error": "Operation Failed",
                    "warning": "Warning",
                    "info": "Information",
                    "confirm": "Confirm",
                    "cancel": "Cancel",
                    "yes": "Yes",
                    "no": "No",
                    "no_content_to_save": "No content to save",
                    "result_saved_to": "Result saved to: {filename}",
                    "save_failed": "Save failed: {e}",
                    "file_not_exists": "File {file_path} does not exist",
                    "load_tag_data_failed": "Failed to load tag data: {e}",
                    "please_select_tags_to_delete": "Please select tags to delete first",
                    "delete_operation_completed": "Delete operation completed!\nModified {count} records",
                    "execute_delete_failed": "Failed to execute delete operation: {e}",
                    "file_backed_up_to": "File backed up to:\n{backup_path}",
                    "backup_failed": "Backup failed: {e}",
                    "file_organizer_init_failed": "File organizer initialization failed: {e}",
                    "please_select_folder_to_read": "Please select a folder to read first",
                    "selected_folder_not_exists": "Selected folder does not exist",
                    "startup_script_not_found": "Startup script not found: {script}",
                    "start_article_reader_failed": "Failed to start article reader: {e}",
                    "batch_reading_completed": "Batch reading completed!\n\nSuccessful reads: {success}\nFailed reads: {failed}\n\nResults saved to: ai_organize_result.json",
                    "batch_document_reading_failed": "Batch document reading failed: {error}",
                    "please_select_directories": "Please select source and target directories first",
                    "ai_organize_failed": "AI organization failed: {error}",
                    "delete_completed": "Delete completed",
                    "delete_failed": "Delete failed",
                    "delete_source_files_error": "Error deleting source files: {error}",
                    "transfer_logs_not_enabled": "Transfer logs feature not enabled",
                    "show_transfer_logs_failed": "Failed to show transfer logs: {error}",
                    "show_duplicate_remover_failed": "Failed to show duplicate remover dialog: {e}",
                    "open_classification_rules_failed": "Failed to open classification rules manager: {e}",
                    "show_ai_model_config_failed": "Failed to show AI model config: {e}",
                    "open_tag_manager_failed": "Failed to open tag manager: {e}",
                    "open_tag_optimizer_failed": "Failed to open tag optimizer: {e}",
                    "start_multi_task_reader_failed": "Failed to start multi-task reader manager: {e}",
                    "start_multi_process_reader_failed": "Failed to start multi-process reader manager: {e}",
                    "i18n_module_not_loaded": "I18n module not loaded, language settings unavailable",
                    "refresh_drives_failed": "Failed to refresh drives: {e}",
                    "please_select_directories_to_organize": "Please select directories to organize first",
                    "please_select_new_directory_location": "Please select new directory location first",
                    "please_generate_ai_recommendation": "Please generate AI recommendation first",
                    "directory_structure_created": "Directory structure created successfully!\n\nPlease use AI classification or file classification to migrate files to the new directory.",
                    "create_directory_structure_failed": "Failed to create directory structure: {e}",
                    "please_select_log_record": "Please select a log record first",
                    "please_select_valid_log_record": "Please select a valid log record first",
                    "cannot_load_log_file": "Cannot load log file: {filename}",
                    "show_log_details_failed": "Failed to show log details: {e}",
                    "log_file_not_exists": "Log file does not exist: {filename}",
                    "show_restore_dialog_failed": "Failed to show restore dialog: {e}"
                },
                "errors": {
                    "file_not_found": "File Not Found",
                    "permission_denied": "Permission Denied",
                    "invalid_config": "Invalid Configuration",
                    "network_error": "Network Error",
                    "ai_model_error": "AI Model Error"
                }
            }
            self._save_language_file(en_us_file, en_us_translations)

    def _save_language_file(self, file_path: Path, translations: Dict[str, Any]):
        """保存语言文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)
            logger.info(f"创建语言文件: {file_path}")
        except Exception as e:
            logger.error(f"创建语言文件失败 {file_path}: {e}")

    def get_text(self, key: str, section: str = "app", **kwargs) -> str:
        """
        获取翻译文本

        Args:
            key: 文本键
            section: 文本分类
            **kwargs: 格式化参数

        Returns:
            翻译后的文本
        """
        try:
            # 获取当前语言的翻译
            current_translations = self.translations.get(self.current_language, {})
            section_translations = current_translations.get(section, {})
            text = section_translations.get(key, key)
            
            # 如果当前语言没有找到，尝试默认语言
            if text == key and self.current_language != self.default_language:
                default_translations = self.translations.get(self.default_language, {})
                default_section = default_translations.get(section, {})
                text = default_section.get(key, key)
            
            # 格式化文本
            if kwargs:
                try:
                    text = text.format(**kwargs)
                except (KeyError, ValueError):
                    logger.warning(f"文本格式化失败: {key}, 参数: {kwargs}")
            
            return text
        except Exception as e:
            logger.error(f"获取翻译文本失败: {key}, 错误: {e}")
            return key

    def set_language(self, language_code: str) -> bool:
        """
        设置当前语言

        Args:
            language_code: 语言代码

        Returns:
            是否设置成功
        """
        if language_code in self.translations:
            self.current_language = language_code
            logger.info(f"语言切换为: {language_code}")
            return True
        else:
            logger.warning(f"不支持的语言: {language_code}")
            return False

    def get_available_languages(self) -> List[str]:
        """
        获取可用语言列表

        Returns:
            可用语言代码列表
        """
        return list(self.translations.keys())

    def detect_system_language(self) -> str:
        """
        检测系统语言

        Returns:
            检测到的语言代码
        """
        try:
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                # 转换语言代码格式
                if system_locale.startswith('zh'):
                    return 'zh-CN'
                elif system_locale.startswith('en'):
                    return 'en-US'
        except Exception as e:
            logger.error(f"检测系统语言失败: {e}")
        
        return self.default_language

    def get_language_info(self, language_code: str) -> Dict[str, str]:
        """
        获取语言信息

        Args:
            language_code: 语言代码

        Returns:
            语言信息字典
        """
        language_names = {
            'zh-CN': '中文简体',
            'en-US': 'English'
        }
        
        return {
            'code': language_code,
            'name': language_names.get(language_code, language_code),
            'available': language_code in self.translations
        }

    def reload_language_files(self):
        """重新加载语言文件"""
        self.translations.clear()
        self._load_language_files()
        logger.info("语言文件重新加载完成")


# 全局实例
_i18n_manager = None


def get_i18n_manager() -> I18nManager:
    """
    获取国际化管理器实例（单例模式）

    Returns:
        国际化管理器实例
    """
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager

def reset_i18n_manager():
    """重置国际化管理器实例（用于测试和调试）"""
    global _i18n_manager
    _i18n_manager = None


def t(key: str, section: str = "app", **kwargs) -> str:
    """
    获取翻译文本的便捷函数

    Args:
        key: 文本键
        section: 文本分类
        **kwargs: 格式化参数

    Returns:
        翻译后的文本
    """
    return get_i18n_manager().get_text(key, section, **kwargs)


if __name__ == "__main__":
    # 测试代码
    i18n = I18nManager()
    
    # 测试基本翻译
    print("当前语言:", i18n.current_language)
    print("应用标题:", i18n.get_text("title", "app"))
    print("设置:", i18n.get_text("settings", "app"))
    
    # 测试语言切换
    i18n.set_language("en-US")
    print("切换后语言:", i18n.current_language)
    print("应用标题:", i18n.get_text("title", "app"))
    print("设置:", i18n.get_text("settings", "app"))
    
    # 测试便捷函数
    print("便捷函数测试:", t("title", "app"))
    
    # 显示可用语言
    print("可用语言:", i18n.get_available_languages()) 