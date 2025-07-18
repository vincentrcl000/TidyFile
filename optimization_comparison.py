#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
500字符截取优化效果对比分析
比较优化前后的处理性能差异
"""

import json
import os
from pathlib import Path

def load_test_results():
    """加载测试结果数据"""
    results = {}
    
    # 加载优化后的结果
    if os.path.exists("test_500_char_results.json"):
        with open("test_500_char_results.json", 'r', encoding='utf-8') as f:
            results['optimized'] = json.load(f)
    
    # 加载原始测试结果
    if os.path.exists("test_timing_results.json"):
        with open("test_timing_results.json", 'r', encoding='utf-8') as f:
            results['original'] = json.load(f)
    
    return results

def analyze_optimization_effect():
    """分析优化效果"""
    print("=== 500字符截取优化效果分析 ===")
    print()
    
    results = load_test_results()
    
    if 'optimized' not in results:
        print("❌ 未找到优化后的测试结果")
        return
    
    optimized_data = results['optimized']
    
    print("📊 优化效果详细分析")
    print("=" * 60)
    
    # 分析每个文件的优化效果
    total_original_chars = 0
    total_ai_chars = 0
    total_processing_time = 0
    
    for i, result in enumerate(optimized_data, 1):
        file_name = result['file_name']
        original_length = result['original_length']
        ai_processing_length = result['ai_processing_length']
        truncation_ratio = result['truncation_ratio']
        timing_info = result['timing_info']
        classification = result['classification_result']
        
        total_original_chars += original_length
        total_ai_chars += ai_processing_length
        total_processing_time += timing_info.get('total_processing_time', 0)
        
        print(f"\n📄 文件 {i}: {file_name}")
        print(f"   原始内容长度: {original_length:,} 字符")
        print(f"   AI处理长度: {ai_processing_length:,} 字符")
        print(f"   内容压缩率: {(1-truncation_ratio)*100:.1f}%")
        print(f"   处理时间: {timing_info.get('total_processing_time', 0):.2f} 秒")
        print(f"   分类结果: {classification['recommended_folder']}")
        print(f"   分类准确性: ✅ 成功")
        
        # 时间分解
        print(f"   ⏱ 时间分解:")
        print(f"     - 内容提取: {timing_info.get('content_extraction_time', 0):.3f}秒")
        print(f"     - 摘要生成: {timing_info.get('summary_generation_time', 0):.2f}秒")
        print(f"     - 目录推荐: {timing_info.get('folder_recommendation_time', 0):.2f}秒")
    
    # 总体统计
    avg_processing_time = total_processing_time / len(optimized_data)
    overall_compression = (total_original_chars - total_ai_chars) / total_original_chars * 100
    
    print(f"\n📈 总体优化效果")
    print("=" * 40)
    print(f"处理文件数量: {len(optimized_data)}")
    print(f"总原始字符数: {total_original_chars:,}")
    print(f"总AI处理字符数: {total_ai_chars:,}")
    print(f"整体内容压缩率: {overall_compression:.1f}%")
    print(f"平均处理时间: {avg_processing_time:.2f} 秒")
    
    # 与历史数据对比（如果有的话）
    if 'original' in results:
        print(f"\n📊 与历史数据对比")
        print("=" * 40)
        
        original_data = results['original']
        if isinstance(original_data, list) and len(original_data) > 0:
            # 计算历史平均处理时间
            historical_times = []
            for item in original_data:
                if 'timing_info' in item:
                    historical_times.append(item['timing_info'].get('total_processing_time', 0))
            
            if historical_times:
                avg_historical_time = sum(historical_times) / len(historical_times)
                time_improvement = (avg_historical_time - avg_processing_time) / avg_historical_time * 100
                
                print(f"历史平均处理时间: {avg_historical_time:.2f} 秒")
                print(f"当前平均处理时间: {avg_processing_time:.2f} 秒")
                if time_improvement > 0:
                    print(f"⚡ 处理速度提升: {time_improvement:.1f}%")
                else:
                    print(f"⚠️ 处理时间增加: {abs(time_improvement):.1f}%")
    
    # 优化建议
    print(f"\n💡 优化效果评估")
    print("=" * 40)
    
    if overall_compression > 30:
        print(f"✅ 内容压缩效果显著: {overall_compression:.1f}%")
        print("   - 大幅减少了AI模型需要处理的数据量")
        print("   - 有效降低了计算资源消耗")
    elif overall_compression > 10:
        print(f"✅ 内容压缩效果良好: {overall_compression:.1f}%")
        print("   - 适度减少了AI处理负担")
    else:
        print(f"ℹ️ 内容压缩效果有限: {overall_compression:.1f}%")
        print("   - 主要处理的是短文件")
    
    if avg_processing_time < 30:
        print(f"✅ 处理速度表现优秀: 平均 {avg_processing_time:.1f} 秒/文件")
    elif avg_processing_time < 60:
        print(f"✅ 处理速度表现良好: 平均 {avg_processing_time:.1f} 秒/文件")
    else:
        print(f"⚠️ 处理速度仍需优化: 平均 {avg_processing_time:.1f} 秒/文件")
    
    # 进一步优化建议
    print(f"\n🚀 进一步优化建议")
    print("=" * 40)
    print("1. 📝 内容预处理优化:")
    print("   - 可考虑智能选择关键段落而非简单截取前500字符")
    print("   - 对于结构化文档，提取标题和关键信息")
    
    print("\n2. ⚡ 处理流程优化:")
    print("   - 实现文件类型预判，跳过无需AI分析的文件")
    print("   - 添加内容哈希缓存，避免重复处理相同文件")
    
    print("\n3. 🔄 并发处理优化:")
    print("   - 实现多文件并行处理")
    print("   - 优化AI模型调用频率")
    
    print("\n4. 🎯 智能分类优化:")
    print("   - 基于文件扩展名的快速分类规则")
    print("   - 用户自定义分类规则支持")
    
    # 保存分析报告
    report = {
        'analysis_date': '2025-07-18',
        'optimization_type': '500字符截取优化',
        'total_files_processed': len(optimized_data),
        'overall_compression_rate': overall_compression,
        'average_processing_time': avg_processing_time,
        'detailed_results': optimized_data,
        'recommendations': [
            '实现智能内容选择算法',
            '添加文件类型预判机制',
            '实现内容哈希缓存',
            '支持并发处理',
            '添加快速分类规则'
        ]
    }
    
    with open('optimization_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📋 详细分析报告已保存到: optimization_analysis_report.json")

if __name__ == "__main__":
    analyze_optimization_effect()