# -*- coding: utf-8 -*-
"""
PaddleOCR 异步 Layout Parsing 工具
支持大文件自动拆分处理，避免超时和 413 错误
"""
import base64
import json
import os
import requests
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# 导入 PDF 拆分器
from pdf_splitter import split_pdf, cleanup_temp_files

# API 配置
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
TOKEN = "01ad53b81383d257dd9610407bf94d330315a502"
MODEL = "PaddleOCR-VL-1.5"
MAX_FILE_SIZE_MB = 30  # 超过此大小自动拆分（目标：每份 <30MB）


def submit_job(file_path, options=None):
    """提交 OCR 作业"""
    headers = {
        "Authorization": f"bearer {TOKEN}",
    }
    
    optional_payload = options or {
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    }
    
    print(f"  提交作业: {Path(file_path).name}")
    
    if str(file_path).startswith("http"):
        headers["Content-Type"] = "application/json"
        payload = {
            "fileUrl": file_path,
            "model": MODEL,
            "optionalPayload": optional_payload
        }
        response = requests.post(JOB_URL, json=payload, headers=headers, timeout=60)
    else:
        if not os.path.exists(file_path):
            print(f"  错误: 文件不存在 - {file_path}")
            return None
            
        data = {
            "model": MODEL,
            "optionalPayload": json.dumps(optional_payload)
        }
        
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                JOB_URL, 
                headers={"Authorization": f"bearer {TOKEN}"}, 
                data=data, 
                files=files,
                timeout=120
            )
    
    if response.status_code != 200:
        print(f"  提交失败: {response.status_code}")
        if response.status_code == 413:
            print("  文件太大，需要拆分")
        return None
    
    job_id = response.json()["data"]["jobId"]
    print(f"  作业 ID: {job_id}")
    return job_id


def poll_job_result(job_id):
    """轮询获取作业结果"""
    headers = {"Authorization": f"bearer {TOKEN}"}
    jsonl_url = ""
    
    while True:
        try:
            response = requests.get(f"{JOB_URL}/{job_id}", headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()["data"]
            state = data["state"]
            
            if state == 'pending':
                time.sleep(3)
            elif state == 'running':
                try:
                    progress = data['extractProgress']
                    total = progress.get('totalPages', '?')
                    extracted = progress.get('extractedPages', 0)
                    print(f"    处理中: {extracted}/{total} 页", end='\r')
                except:
                    pass
                time.sleep(3)
            elif state == 'done':
                progress = data['extractProgress']
                print(f"    完成: {progress.get('extractedPages', 0)} 页      ")
                jsonl_url = data['resultUrl']['jsonUrl']
                break
            elif state == "failed":
                error_msg = data.get('errorMsg', '未知错误')
                print(f"    失败: {error_msg}")
                return None
            
        except Exception as e:
            print(f"    轮询异常: {e}")
            time.sleep(5)
    
    if not jsonl_url:
        return None
    
    # 下载结果
    try:
        response = requests.get(jsonl_url, timeout=120)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"    下载失败: {e}")
        return None


def parse_jsonl(jsonl_text, output_path, save_images=True):
    """解析 JSONL 结果，返回 Markdown 内容和页数"""
    lines = jsonl_text.strip().split('\n')
    all_pages = []
    page_num = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        try:
            result = json.loads(line)["result"]
            for res in result.get("layoutParsingResults", []):
                md_text = res.get("markdown", {}).get("text", "")
                all_pages.append(md_text)
                
                # 保存图片
                if save_images:
                    _save_images(res, output_path, page_num)
                
                page_num += 1
        except Exception as e:
            print(f"    解析警告: {e}")
            continue
    
    return all_pages, page_num


def _save_images(res, output_path, page_num):
    """保存图片到本地"""
    if "markdown" in res and "images" in res["markdown"]:
        for img_path, img_url in res["markdown"]["images"].items():
            try:
                clean_path = img_path.lstrip('/').replace(':', '_')
                full_path = output_path / "assets" / clean_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                img_response = requests.get(img_url, timeout=30)
                if img_response.status_code == 200:
                    with open(full_path, "wb") as f:
                        f.write(img_response.content)
            except:
                pass
    
    if "outputImages" in res:
        for img_name, img_url in res["outputImages"].items():
            try:
                img_response = requests.get(img_url, timeout=30)
                if img_response.status_code == 200:
                    assets_dir = output_path / "assets"
                    assets_dir.mkdir(exist_ok=True)
                    filename = assets_dir / f"page_{page_num:04d}_{img_name}.jpg"
                    with open(filename, "wb") as f:
                        f.write(img_response.content)
            except:
                pass


def process_small_file(file_path, output_dir, save_images=True):
    """处理小文件（直接上传）"""
    job_id = submit_job(str(file_path))
    if not job_id:
        return None, 0
    
    jsonl_text = poll_job_result(job_id)
    if not jsonl_text:
        return None, 0
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    return parse_jsonl(jsonl_text, output_path, save_images)


def split_pdf_adaptive(file_path, max_size_mb=30, initial_pages_per_chunk=5):
    """
    自适应拆分 PDF，确保每份文件 < max_size_mb
    如果拆分到单页还超过限制，则报错
    
    Returns:
        list: 拆分后的文件路径列表，或 None（如果无法拆分）
    """
    import fitz
    
    file_path = Path(file_path)
    doc = fitz.open(str(file_path))
    total_pages = len(doc)
    doc.close()
    
    file_size_mb = file_path.stat().st_size / 1024 / 1024
    print(f"  文件大小: {file_size_mb:.2f} MB, 总页数: {total_pages}")
    
    # 计算需要的拆分粒度
    pages_per_chunk = initial_pages_per_chunk
    
    while True:
        # 估算每份大小
        estimated_chunk_size = file_size_mb / (total_pages / pages_per_chunk)
        print(f"  尝试 {pages_per_chunk} 页/份，估算每份大小: {estimated_chunk_size:.2f} MB")
        
        if estimated_chunk_size <= max_size_mb:
            # 预估可以，实际拆分验证
            print(f"  开始拆分...")
            chunk_files = split_pdf(file_path, pages_per_chunk)
            
            if not chunk_files:
                return None
            
            # 验证实际大小
            all_valid = True
            for chunk_file in chunk_files:
                chunk_size = Path(chunk_file).stat().st_size / 1024 / 1024
                if chunk_size > max_size_mb:
                    print(f"  警告: {Path(chunk_file).name} 实际大小 {chunk_size:.2f} MB 超过限制")
                    all_valid = False
                    break
            
            if all_valid:
                print(f"  ✓ 拆分完成: {len(chunk_files)} 份")
                return chunk_files
            
            # 有文件还太大，清理后继续减小粒度
            cleanup_temp_files(chunk_files)
        
        # 减小粒度
        pages_per_chunk = max(1, pages_per_chunk // 2)
        
        # 检查是否已到单页
        if pages_per_chunk == 1:
            # 检查单页是否超过限制
            single_page_files = split_pdf(file_path, 1)
            if not single_page_files:
                return None
            
            oversized_pages = []
            for page_file in single_page_files:
                page_size = Path(page_file).stat().st_size / 1024 / 1024
                if page_size > max_size_mb:
                    page_num = Path(page_file).stem.split('_')[-1]
                    oversized_pages.append((page_num, page_size))
            
            if oversized_pages:
                cleanup_temp_files(single_page_files)
                print(f"\n  ✗ 错误: 以下单页超过 {max_size_mb}MB 限制，无法处理:")
                for page_num, size in oversized_pages[:5]:  # 只显示前5个
                    print(f"      第 {page_num} 页: {size:.2f} MB")
                if len(oversized_pages) > 5:
                    print(f"      ... 还有 {len(oversized_pages) - 5} 页")
                return None
            
            print(f"  ✓ 已拆分到单页: {len(single_page_files)} 页")
            return single_page_files
        
        print(f"  估算大小仍超过限制，减小到 {pages_per_chunk} 页/份")


def process_large_pdf(file_path, output_dir, save_images=True):
    """处理大 PDF（自适应拆分后分批处理）"""
    
    # 自适应拆分
    chunk_files = split_pdf_adaptive(file_path, max_size_mb=MAX_FILE_SIZE_MB, initial_pages_per_chunk=5)
    if not chunk_files:
        return None, 0
    
    all_pages = []
    total_pages = 0
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"  开始处理 {len(chunk_files)} 份...")
    
    for i, chunk_file in enumerate(chunk_files, 1):
        print(f"\n  处理第 {i}/{len(chunk_files)} 份...")
        pages, count = process_small_file(chunk_file, output_dir, save_images)
        
        if pages:
            all_pages.extend(pages)
            total_pages += count
        else:
            print(f"  第 {i} 份处理失败，跳过")
        
        time.sleep(1)  # 避免请求过快
    
    # 清理临时文件
    cleanup_temp_files(chunk_files)
    
    return all_pages, total_pages


def process_file(file_path, output_dir="resources/books/00_待分类", save_images=True):
    """处理单个文件（自动判断大小）"""
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"错误: 文件不存在 - {file_path}")
        return False
    
    ext = file_path.suffix.lower()
    if ext not in ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        print(f"错误: 不支持的格式 - {ext}")
        return False
    
    file_size_mb = file_path.stat().st_size / 1024 / 1024
    
    # 清理文件名
    import re
    base_name = file_path.stem[:50]
    base_name = re.sub(r' \(z-library[^)]*\)', '', base_name)
    base_name = re.sub(r' \([^)]*\)$', '', base_name)
    base_name = base_name.strip()
    
    print(f"\n{'='*60}")
    print(f"处理: {base_name}")
    print(f"  大小: {file_size_mb:.2f} MB")
    print(f"  类型: {ext.upper()}")
    print(f"{'='*60}")
    
    # 根据文件大小选择处理方式
    if ext == '.pdf' and file_size_mb > MAX_FILE_SIZE_MB:
        all_pages, page_count = process_large_pdf(file_path, output_dir, save_images)
    else:
        all_pages, page_count = process_small_file(file_path, output_dir, save_images)
    
    if not all_pages:
        print("✗ 处理失败")
        return False
    
    # 合并所有页面
    final_content = "\n\n---\n\n".join(all_pages)
    
    # 添加 Frontmatter
    timestamp = datetime.now().strftime("%Y-%m-%d")
    frontmatter = f"""---
title: "{base_name}"
date: {timestamp}
source: "{file_path.name}"
type: "Book"
tags: ["OCR", "书籍"]
pages: {page_count}
---

"""
    
    final_content = frontmatter + final_content
    
    # 保存
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    md_file = output_path / f"{base_name}.md"
    
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(final_content)
    
    file_size_kb = os.path.getsize(md_file) / 1024
    print(f"\n✓ 已保存: {md_file.name}")
    print(f"  共 {page_count} 页, {file_size_kb:.1f} KB")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="PaddleOCR 异步 Layout Parsing - PDF/图片转 Markdown"
    )
    parser.add_argument("input", help="输入文件或目录路径")
    parser.add_argument("-o", "--output", default="resources/books/00_待分类", help="输出目录 (默认: resources/books/00_待分类)")
    parser.add_argument("--no-images", action="store_true", help="不下载图片")
    # 注意: 现在使用自适应拆分，自动调整页数直到每份 <30MB
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = args.output
    save_images = not args.no_images
    
    if input_path.is_file():
        success = process_file(input_path, output_dir, save_images)
        sys.exit(0 if success else 1)
    
    elif input_path.is_dir():
        files = (
            list(input_path.glob("*.pdf")) +
            list(input_path.glob("*.jpg")) +
            list(input_path.glob("*.png"))
        )
        
        if not files:
            print(f"未找到可处理文件: {input_path}")
            sys.exit(1)
        
        print(f"\n批量处理: {len(files)} 个文件")
        
        success_count = 0
        for i, file in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}]", end=" ")
            if process_file(file, output_dir, save_images):
                success_count += 1
        
        print(f"\n{'='*60}")
        print(f"完成: {success_count}/{len(files)} 个文件成功")
        
        sys.exit(0 if success_count == len(files) else 1)
    
    else:
        print(f"错误: 路径不存在 - {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
