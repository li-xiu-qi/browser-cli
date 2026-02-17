#!/usr/bin/env python3
"""
简易图片提取器 - 从文章中提取指定序号的图片
用法: uv run python extract.py <文章.md> <序号1,序号2,...>
"""
import re
import sys
import requests
from pathlib import Path

def extract_images(md_file: str, indices: list, output_dir: str = "0_Inbox/image-staging"):
    md_path = Path(md_file)
    if not md_path.exists():
        print(f"❌ 文件不存在: {md_file}")
        return
    
    # 读取markdown
    content = md_path.read_text(encoding='utf-8')
    
    # 提取所有图片
    pattern = r'!\[([^\]]*)\]\((https?://[^)]+)\)'
    images = re.findall(pattern, content)
    
    print(f"📄 文章共有 {len(images)} 张图片")
    print(f"🎯 要提取: {indices}")
    
    # 准备输出目录
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    # 下载指定图片
    headers = {'User-Agent': 'Mozilla/5.0'}
    downloaded = []
    
    for idx in indices:
        if idx < 1 or idx > len(images):
            print(f"⚠️  序号 {idx} 超出范围")
            continue
        
        alt, url = images[idx - 1]  # 转为0基索引
        ext = '.png' if 'png' in url else '.jpg'
        filename = f"{md_path.stem}_{idx:02d}{ext}"
        filepath = out / filename
        
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 1000:
                filepath.write_bytes(resp.content)
                downloaded.append((idx, filename, alt))
                print(f"✅ [{idx}] {filename} ({len(resp.content)//1024}KB)")
            else:
                print(f"❌ [{idx}] 下载失败或文件过小")
        except Exception as e:
            print(f"❌ [{idx}] 错误: {e}")
    
    print(f"\n📊 完成: {len(downloaded)}/{len(indices)} 张")
    print(f"📁 保存到: {out}")
    return downloaded

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: uv run python extract.py <文章.md> <序号1,序号2,...>")
        print("示例: uv run python extract.py '文章.md' 1,3,5,8")
        sys.exit(1)
    
    md_file = sys.argv[1]
    indices = [int(x.strip()) for x in sys.argv[2].split(',')]
    extract_images(md_file, indices)
