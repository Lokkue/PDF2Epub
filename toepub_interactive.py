#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Toepub 交互式转换工具入口
"""

import os
import sys
import inquirer

# 确保当前目录和scripts目录在路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入交互式转换脚本的函数
sys.path.append(os.path.join(current_dir, 'scripts'))
from interactive_convert import get_pdf_files, select_pdf_file, get_output_path

def main():
    """
    主函数 - 交互式转换入口
    """
    print("=== PDF2Epub 交互式转换工具 ===\n")
    
    # 获取PDF文件列表
    pdf_files = get_pdf_files()
    
    # 选择PDF文件
    input_path = select_pdf_file(pdf_files)
    
    # 获取输出路径
    output_path = get_output_path(input_path)
    
    # 获取main.py的路径
    main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
    
    # 构建命令
    cmd = [sys.executable, main_script, input_path, '-o', output_path]
    
    # 询问日志详细程度
    questions = [
        inquirer.List('log_level',
                     message='选择日志级别',
                     choices=[
                         ('用户模式 - 只显示警告和错误', 'user'),
                         ('信息模式 - 显示处理进度和基本统计信息', 'info'),
                         ('开发模式 - 显示详细技术信息', 'dev'),
                         ('调试模式 - 最详细的诊断信息', 'debug')
                     ],
                     default='user')
    ]
    
    answers = inquirer.prompt(questions)
    log_level = answers['log_level']
    
    if log_level == 'debug':
        cmd.append('--debug')
    elif log_level == 'info':
        cmd.append('-v')
    elif log_level == 'dev':
        cmd.append('-vv')
    # 用户模式不需要添加参数
    
    # 询问是否限制页数
    questions = [
        inquirer.Confirm('limit_pages',
                         message='是否限制处理页数？',
                         default=False)
    ]
    
    answers = inquirer.prompt(questions)
    
    if answers['limit_pages']:
        questions = [
            inquirer.Text('max_pages',
                         message='最大处理页数',
                         validate=lambda _, x: x.isdigit() and int(x) > 0,
                         default='10')
        ]
        
        answers = inquirer.prompt(questions)
        cmd.extend(['--max-pages', answers['max_pages']])
    
    # 运行命令
    print(f"\n开始转换: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")
    print(f"命令: {' '.join(cmd)}\n")
    
    try:
        import subprocess
        subprocess.run(cmd, check=True)
        print(f"\n转换完成！输出文件: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"\n转换失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
