#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移命令管理模块：根据AI分类结果生成迁移命令，支持批量预览。
"""
import logging
class MigrationPlanner:
    def plan_migrations(self, file_list, directory_json, ai_classifier):
        plan = []
        logging.info(f"开始生成迁移计划，共{len(file_list)}个文件")
        print(f"[MigrationPlanner] 开始生成迁移计划，共{len(file_list)}个文件")
        for file_path in file_list:
            match = ai_classifier.get_best_match(file_path, directory_json)
            best_dir = match.get('best_match')
            logging.info(f"文件: {file_path} 推荐目录: {best_dir}")
            print(f"[MigrationPlanner] 文件: {file_path} 推荐目录: {best_dir}")
            if best_dir:
                plan.append({
                    'source': file_path,
                    'target_dir': best_dir,
                    'operation': 'copy',
                    'ai_score': match.get('scores', [])
                })
            else:
                plan.append({
                    'source': file_path,
                    'target_dir': None,
                    'operation': None,
                    'ai_score': match.get('scores', [])
                })
        logging.info(f"迁移计划生成完成，总{len(plan)}条")
        print(f"[MigrationPlanner] 迁移计划生成完成，总{len(plan)}条")
        return plan
    def preview_plan(self, plan):
        preview = []
        logging.info(f"预览迁移计划，共{len(plan)}条")
        print(f"[MigrationPlanner] 预览迁移计划，共{len(plan)}条")
        for item in plan:
            preview.append(f"{item['source']} -> {item['target_dir']} [{item['operation']}] (AI:{item['ai_score']})")
            print(f"[MigrationPlanner] {item['source']} -> {item['target_dir']} [{item['operation']}] (AI:{item['ai_score']})")
        return preview 