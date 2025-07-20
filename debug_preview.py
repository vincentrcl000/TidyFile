#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试预览功能的脚本
"""

import os
import json
import logging
from pathlib import Path
from file_organizer_ai import FileOrganizer

def debug_preview_issue():
    """调试预览功能只处理10个文件的问题"""
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            # logging.FileHandler('debug_preview.log', encoding='utf-8'),  # 已禁用文件日志
            logging.StreamHandler()
        ]
    )
    
    print("=== 开始调试预览功能 ===")
    logging.info("开始调试预览功能")
    
    # 初始化AI组织器
    try:
        ai_organizer = FileOrganizer()
        print("AI组织器初始化成功")
        logging.info("AI组织器初始化成功")
    except Exception as e:
        print(f"AI组织器初始化失败: {e}")
        logging.error(f"AI组织器初始化失败: {e}")
        return
    
    # 模拟GUI中的预览过程
    source_directory = "d:\\保险行业资料\\寿险2024"  # 用户的源目录
    target_directory = "d:\\保险行业资料"  # 用户的目标目录
    
    print(f"源目录: {source_directory}")
    print(f"目标目录: {target_directory}")
    
    # 检查目录是否存在
    if not os.path.exists(source_directory):
        print(f"源目录不存在: {source_directory}")
        logging.error(f"源目录不存在: {source_directory}")
        return
        
    if not os.path.exists(target_directory):
        print(f"目标目录不存在: {target_directory}")
        logging.error(f"目标目录不存在: {target_directory}")
        return
    
    try:
        # 扫描文件
        print("正在扫描源文件...")
        source_files = ai_organizer.scan_files(source_directory)
        print(f"扫描到 {len(source_files)} 个文件")
        logging.info(f"扫描到 {len(source_files)} 个文件")
        
        if not source_files:
            print("源目录中没有找到文件")
            return
        
        # 显示前几个文件
        print("\n前10个文件:")
        for i, file_info in enumerate(source_files[:10]):
            print(f"  {i+1}. {file_info['name']}")
        
        # 模拟预览过程
        preview_results = []
        ai_result_list = []
        processed_count = 0
        
        print(f"\n开始处理文件...")
        
        for i, file_info in enumerate(source_files):
            file_path = str(file_info['path'])
            filename = str(file_info['name'])
            
            print(f"正在处理文件 {i+1}/{len(source_files)}: {filename}")
            logging.info(f"正在处理文件 {i+1}/{len(source_files)}: {filename}")
            
            try:
                # 使用AI分析文件
                result = ai_organizer.analyze_and_classify_file(file_path, target_directory)
                
                success = result.get('success', False)
                folder = result.get('recommended_folder', '')
                reason = result.get('match_reason', '')
                summary = result.get('content_summary', '')
                timing_info = result.get('timing_info', {})
                
                # 构建AI结果JSON条目
                ai_result_item = {
                    "源文件路径": file_path,
                    "文件摘要": summary,
                    "最匹配的目标目录": folder if success else "无推荐",
                    "匹配理由": reason if reason else ""
                }
                
                ai_result_list.append(ai_result_item)
                processed_count += 1
                
                print(f"  处理成功: {folder if success else '无推荐'}")
                logging.info(f"文件 {filename} 处理成功: {folder if success else '无推荐'}")
                
            except Exception as file_error:
                print(f"  处理失败: {file_error}")
                logging.error(f"处理文件 {filename} 失败: {file_error}")
                
                # 即使单个文件失败，也继续处理下一个文件
                ai_result_item = {
                    "源文件路径": file_path,
                    "文件摘要": "",
                    "最匹配的目标目录": "处理失败",
                    "匹配理由": f"处理失败: {str(file_error)}"
                }
                ai_result_list.append(ai_result_item)
                processed_count += 1
        
        print(f"\n处理完成，共处理 {processed_count} 个文件")
        logging.info(f"处理完成，共处理 {processed_count} 个文件")
        
        # 保存结果
        debug_result_path = "debug_preview_result.json"
        with open(debug_result_path, 'w', encoding='utf-8') as f:
            json.dump(ai_result_list, f, ensure_ascii=False, indent=2)
        
        print(f"调试结果已保存到: {debug_result_path}")
        print(f"结果文件包含 {len(ai_result_list)} 个条目")
        
        # 比较与原始preview_ai_result.json的差异
        original_result_path = "preview_ai_result.json"
        if os.path.exists(original_result_path):
            with open(original_result_path, 'r', encoding='utf-8') as f:
                original_results = json.load(f)
            print(f"\n原始预览结果包含 {len(original_results)} 个条目")
            print(f"调试结果包含 {len(ai_result_list)} 个条目")
            
            if len(original_results) != len(ai_result_list):
                print("发现差异！调试结果与原始结果数量不同")
            else:
                print("数量一致，可能是其他问题")
        
    except Exception as e:
        print(f"调试过程中发生异常: {e}")
        logging.error(f"调试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        logging.error(traceback.format_exc())

if __name__ == "__main__":
    debug_preview_issue()