#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path


def read_md_file(file_path):
    """
    读取 Markdown 文件并返回其内容字符串。

    参数:
        file_path (str 或 Path): Markdown 文件的路径。

    返回:
        str: 文件内容。

    异常:
        FileNotFoundError: 文件不存在时抛出。
        IOError: 读取失败时抛出。
    """
    path = Path(file_path)
    try:
        # 使用 UTF-8 编码读取，这是 Markdown 文件最常用的编码
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        raise FileNotFoundError(f"错误：文件 '{file_path}' 不存在。")
    except Exception as e:
        raise IOError(f"读取文件时出错：{e}")


def main():
    # 从命令行参数获取文件路径，若未提供则提示用户输入
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = input("请输入 Markdown 文件的路径：").strip()
        if not file_path:
            print("错误：未输入文件路径。")
            sys.exit(1)

    try:
        content = read_md_file(file_path)
        print(content)  # 输出文件字符串内容
    except (FileNotFoundError, IOError) as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()