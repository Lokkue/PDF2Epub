#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交互式PDF转EPUB工具
提供方向键选择文件和输出路径的功能
"""

import os
import sys
import inquirer
import subprocess
from pathlib import Path

def get_pdf_files(directory=None):
    """
    获取指定目录下的所有PDF文件
    
    参数:
        directory: 要搜索的目录，默认为当前目录
        
    返回:
        list: PDF文件路径列表
    """
    if directory is None:
        directory = os.getcwd()
    
    pdf_files = []
    
    # 递归搜索目录下的所有PDF文件
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    return pdf_files

def select_pdf_file(pdf_files):
    """
    让用户选择一个PDF文件
    
    参数:
        pdf_files: PDF文件列表
        
    返回:
        选择的PDF文件路径
    """
    if not pdf_files:
        print("错误: 未找到PDF文件")
        sys.exit(1)
    
    # 将路径转换为相对路径，以便更好地显示
    relative_paths = [os.path.relpath(path) for path in pdf_files]
    
    questions = [
        inquirer.List('pdf_file',
                      message='请选择要转换的PDF文件',
                      choices=relative_paths,
                      carousel=True)
    ]
    
    answers = inquirer.prompt(questions)
    
    # 处理用户取消操作
    if answers is None:
        print("\n操作已取消。")
        sys.exit(0)
    
    selected_index = relative_paths.index(answers['pdf_file'])
    
    return pdf_files[selected_index]

def get_output_path(input_path):
    """
    获取输出文件路径
    
    参数:
        input_path: 输入文件路径
        
    返回:
        str: 输出文件路径
    """
    # 默认输出路径：与输入文件相同的目录，但扩展名为.epub
    default_output = os.path.splitext(input_path)[0] + '.epub'
    
    # 询问用户是否使用默认输出路径
    questions = [
        inquirer.Confirm('use_default',
                         message=f'使用默认输出路径？({os.path.relpath(default_output)})',
                         default=True)
    ]
    
    answers = inquirer.prompt(questions)
    
    # 处理用户取消操作
    if answers is None:
        print("\n操作已取消。")
        sys.exit(0)
    
    if answers['use_default']:
        return default_output
    
    # 让用户选择输出目录
    questions = [
        inquirer.Path('output_dir',
                     message='请选择输出目录',
                     path_type=inquirer.Path.DIRECTORY,
                     default=os.path.dirname(input_path))
    ]
    
    answers = inquirer.prompt(questions)
    
    # 处理用户取消操作
    if answers is None:
        print("\n操作已取消。")
        sys.exit(0)
        
    output_dir = answers['output_dir']
    
    # 让用户输入文件名
    questions = [
        inquirer.Text('filename',
                     message='请输入输出文件名（不含扩展名）',
                     default=os.path.splitext(os.path.basename(input_path))[0])
    ]
    
    answers = inquirer.prompt(questions)
    
    # 处理用户取消操作
    if answers is None:
        print("\n操作已取消。")
        sys.exit(0)
        
    filename = answers['filename']
    
    return os.path.join(output_dir, filename + '.epub')

def run_conversion(input_path, output_path):
    """
    运行转换过程
    
    参数:
        input_path: 输入文件路径
        output_path: 输出文件路径
    """
    # 获取main.py的路径
    main_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py')
    
    # 构建命令
    cmd = [sys.executable, main_script, input_path, '-o', output_path]
    
    # 询问日志级别
    questions = [
        inquirer.List('log_level',
                     message='选择日志级别',
                     choices=[
                         ('基础级别', ''),
                         ('信息级别', '-v'),
                         ('开发者级别', '-vv')
                     ],
                     default='')
    ]
    
    answers = inquirer.prompt(questions)
    
    # 处理用户取消操作
    if answers is None:
        print("\n操作已取消。")
        sys.exit(0)
        
    log_level = answers['log_level']
    if log_level:
        cmd.append(log_level)
    
    # 询问是否启用调试模式
    questions = [
        inquirer.Confirm('debug',
                         message='启用调试模式？',
                         default=False)
    ]
    
    answers = inquirer.prompt(questions)
    
    # 处理用户取消操作
    if answers is None:
        print("\n操作已取消。")
        sys.exit(0)
        
    if answers['debug']:
        cmd.append('--debug')
    
    # 询问是否限制页数
    questions = [
        inquirer.Confirm('limit_pages',
                         message='是否限制处理页数？',
                         default=False)
    ]
    
    answers = inquirer.prompt(questions)
    
    # 处理用户取消操作
    if answers is None:
        print("\n操作已取消。")
        sys.exit(0)
        
    if answers['limit_pages']:
        questions = [
            inquirer.Text('max_pages',
                         message='最大处理页数',
                         validate=lambda _, x: x.isdigit() and int(x) > 0,
                         default='10')
        ]
        
        answers = inquirer.prompt(questions)
        
        # 处理用户取消操作
        if answers is None:
            print("\n操作已取消。")
            sys.exit(0)
            
        cmd.extend(['--max-pages', answers['max_pages']])
    
    # 运行命令
    print(f"\n开始转换: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")
    print(f"命令: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\n转换完成！输出文件: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"\n转换失败: {e}")
        sys.exit(1)

def main():
    """
    主函数
    """
    print("PDF2Epub - 交互式PDF转EPUB工具 v0.1.0\n")
    
    # 获取PDF文件
    pdf_files = get_pdf_files()
    
    # 让用户选择PDF文件
    input_path = select_pdf_file(pdf_files)
    
    # 获取输出路径
    output_path = get_output_path(input_path)
    
    # 运行转换
    run_conversion(input_path, output_path)

if __name__ == "__main__":
    main()
