# -*- coding: utf-8 -*-
"""
PaddleOCR Layout Parsing 工具
基于 Paddle OCR 服务将 PDF/图片转换为 Markdown
"""
import base64
import os
import requests
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

# API 配置
API_URL = "https://b6cdz14b8ch3q5z1.aistudio-app.com/layout-parsing"
TOKEN = "01ad53b81383d257dd9610407bf94d330315a502"


def process_file(file_path, output_dir="output", save_images=True):
    """
    处理单个文件（PDF 或图片）
    
    Args:
        file_path: 输入文件路径
        output_dir: 输出目录
        save_images: 是否保存图片到本地
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"错误: 文件不存在 - {file_path}")
        return False
    
    # 判断文件类型
    ext = file_path.suffix.lower()
    if ext == '.pdf':
        file_type = 0
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        file_type = 1
    else:
        print(f"错误: 不支持的文件格式 - {ext}")
        return False
    
    print(f"处理文件: {file_path.name}")
    print(f"  类型: {'PDF' if file_type == 0 else '图片'}")
    print(f"  大小: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # 读取文件
    with open(file_path, "rb") as f:
        file_bytes = f.read()
        file_data = base64.b64encode(file_bytes).decode("ascii")
    
    # 构建请求
    headers = {
        "Authorization": f"token {TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "file": file_data,
        "fileType": file_type,
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    }
    
    # 发送请求
    print("  正在调用 OCR API...")
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=300)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  错误: API 请求失败 - {e}")
        return False
    
    result = response.json()["result"]
    
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 生成输出文件名
    base_name = file_path.stem[:50]  # 限制长度
    
    # 处理每个布局解析结果
    all_markdown = []
    for i, res in enumerate(result["layoutParsingResults"]):
        md_content = res["markdown"]["text"]
        all_markdown.append(md_content)
        
        # 保存图片
        if save_images and "markdown" in res and "images" in res["markdown"]:
            for img_path, img_url in res["markdown"]["images"].items():
                # 清理图片路径
                clean_img_path = img_path.lstrip('/').replace(':', '_')
                full_img_path = output_path / clean_img_path
                full_img_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    img_response = requests.get(img_url, timeout=30)
                    if img_response.status_code == 200:
                        with open(full_img_path, "wb") as f:
                            f.write(img_response.content)
                        print(f"  图片已保存: {clean_img_path}")
                    else:
                        print(f"  警告: 图片下载失败 - {img_url}")
                except Exception as e:
                    print(f"  警告: 图片下载异常 - {e}")
        
        # 保存 outputImages 中的图片（原始页面图）
        if save_images and "outputImages" in res:
            for img_name, img_url in res["outputImages"].items():
                img_filename = f"{base_name}_page_{i}_{img_name}.jpg"
                img_path = output_path / img_filename
                
                try:
                    img_response = requests.get(img_url, timeout=30)
                    if img_response.status_code == 200:
                        with open(img_path, "wb") as f:
                            f.write(img_response.content)
                        print(f"  页面图片已保存: {img_filename}")
                except Exception as e:
                    print(f"  警告: 页面图片下载异常 - {e}")
    
    # 合并所有 Markdown 内容
    final_markdown = "\n\n---\n\n".join(all_markdown)
    
    # 添加 Frontmatter
    frontmatter = f"""---
title: "{base_name}"
date: {Path(__file__).stat().st_mtime}
source: "{file_path.name}"
type: "Book"
tags: ["OCR", "书籍"]
---

"""
    
    final_content = frontmatter + final_markdown
    
    # 保存 Markdown 文件
    md_filename = output_path / f"{base_name}.md"
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(final_content)
    
    print(f"✓ 完成: {md_filename}")
    print(f"  共 {len(all_markdown)} 页")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="PaddleOCR Layout Parsing - PDF/图片转 Markdown"
    )
    parser.add_argument("input", help="输入文件或目录路径")
    parser.add_argument(
        "-o", "--output",
        default="Areas/书籍",
        help="输出目录 (默认: Areas/书籍)"
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="不下载图片（使用远程链接）"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = args.output
    save_images = not args.no_images
    
    # 处理单个文件
    if input_path.is_file():
        success = process_file(input_path, output_dir, save_images)
        sys.exit(0 if success else 1)
    
    # 处理目录
    elif input_path.is_dir():
        files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.jpg")) + list(input_path.glob("*.png"))
        
        if not files:
            print(f"未找到 PDF 或图片文件: {input_path}")
            sys.exit(1)
        
        print(f"发现 {len(files)} 个文件需要处理")
        print("-" * 50)
        
        success_count = 0
        for file in files:
            if process_file(file, output_dir, save_images):
                success_count += 1
            print()
        
        print("-" * 50)
        print(f"完成: {success_count}/{len(files)} 个文件转换成功")
        sys.exit(0 if success_count == len(files) else 1)
    
    else:
        print(f"错误: 路径不存在 - {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
