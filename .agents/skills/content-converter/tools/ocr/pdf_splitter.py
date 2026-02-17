# -*- coding: utf-8 -*-
"""
PDF 拆分工具 - 使用 PyMuPDF (fitz)
将大 PDF 拆分为小份以便 OCR 处理
"""
import os
import tempfile
from pathlib import Path


def split_pdf(input_path, pages_per_chunk=5):
    """
    将 PDF 拆分为多个小文件
    
    Args:
        input_path: 输入 PDF 路径
        pages_per_chunk: 每份页数
        
    Returns:
        list: 拆分后的文件路径列表
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("错误: 需要安装 PyMuPDF")
        print("运行: uv pip install pymupdf")
        return None
    
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"错误: 文件不存在 - {input_path}")
        return None
    
    # 打开 PDF
    doc = fitz.open(str(input_path))
    total_pages = len(doc)
    
    print(f"PDF 总页数: {total_pages}")
    print(f"每份页数: {pages_per_chunk}")
    num_chunks = (total_pages + pages_per_chunk - 1) // pages_per_chunk
    print(f"预计拆分: {num_chunks} 份")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="pdf_split_")
    output_files = []
    
    # 拆分
    for i in range(0, total_pages, pages_per_chunk):
        # 创建新文档
        new_doc = fitz.open()
        end_page = min(i + pages_per_chunk, total_pages)
        
        # 插入页面
        new_doc.insert_pdf(doc, from_page=i, to_page=end_page-1)
        
        # 保存
        chunk_num = i // pages_per_chunk + 1
        output_path = Path(temp_dir) / f"chunk_{chunk_num:03d}.pdf"
        new_doc.save(str(output_path), garbage=4, deflate=True)
        new_doc.close()
        
        output_files.append(str(output_path))
        file_size = os.path.getsize(output_path) / 1024
        print(f"  创建 {output_path.name}: 页{i+1}-{end_page} ({file_size:.1f} KB)")
    
    doc.close()
    return output_files


def cleanup_temp_files(file_paths):
    """清理临时文件"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"警告: 清理失败 - {e}")
    
    # 尝试删除临时目录
    if file_paths:
        temp_dir = os.path.dirname(file_paths[0])
        try:
            os.rmdir(temp_dir)
        except:
            pass


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python pdf_splitter.py <pdf文件> [每份页数]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    files = split_pdf(input_file, pages)
    
    if files:
        print(f"\n拆分完成: {len(files)} 个文件")
