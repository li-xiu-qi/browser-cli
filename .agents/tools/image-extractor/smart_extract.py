#!/usr/bin/env python3
"""
AI智能图片提取器
1. 分析文章内容，选择性提取有价值的配图
2. 排除风景/装饰/无关图片
3. 可选人工确认

用法: 
  uv run python smart_extract.py <文章.md> [--auto]
"""
import re
import sys
import json
import requests
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# 图片类型判断关键词
CONTENT_KEYWORDS = [
    'chart', 'graph', 'dashboard', 'data', '统计', '趋势', '增长', 'revenue',
    'screenshot', 'terminal', 'cli', 'code', '界面', '终端', '命令行',
    'diagram', 'flow', '架构', '流程', '原理', '结构', '关系', 'system',
    'comparison', '对比', 'vs', 'versus', 'compare',
    'timeline', 'roadmap', '时间线', '路线图', 'history', 'evolution',
    'infographic', '信息图', '可视化',
    'tweet', 'twitter', 'x.com', 'quote', '引用',
    'interface', 'ui', 'product', 'demo', '演示',
    'result', 'output', 'example', '案例', '示例',
]

EXCLUDE_KEYWORDS = [
    '风景', 'scenery', 'landscape', 'nature', '山水', 'nature', 'beauty',
    '头像', 'portrait', 'headshot', 'avatar', 'profile', 'photo of person',
    'banner', 'header', 'hero', 'background', 'bg', 'texture',
    'decoration', '装饰', 'decorative', 'divider', 'line',
    'icon', 'icons', 'button', 'logo', 'brand', 'badge', 'stamp',
    '水印', 'watermark', 'copyright', 'qr', '二维码', 'qrcode',
    'advertisement', '广告', 'ad', 'promo', 'promotion',
    'emoji', '表情', 'sticker', 'gif',
]


def extract_all_images(md_content: str) -> List[Tuple[int, str, str]]:
    """提取文章中所有图片，返回(序号, alt文本, url)"""
    pattern = r'!\[([^\]]*)\]\((https?://[^)]+)\)'
    matches = re.findall(pattern, md_content)
    return [(i+1, alt.strip(), url) for i, (alt, url) in enumerate(matches)]


def analyze_image_relevance(idx: int, alt: str, url: str, article_preview: str, total_images: int) -> Dict:
    """
    分析图片与文章的相关性
    返回: {'should_extract': bool, 'reason': str, 'confidence': int}
    """
    alt_lower = alt.lower()
    url_lower = url.lower()
    preview_lower = article_preview.lower()
    
    # ====== 1. 检查明显排除项 ======
    for kw in EXCLUDE_KEYWORDS:
        if kw in alt_lower or kw in url_lower:
            return {
                'should_extract': False,
                'reason': f'可能是装饰图/无关图 (匹配: {kw})',
                'confidence': 85
            }
    
    # 排除明显的小图标（通过URL特征）
    if any(x in url_lower for x in ['icon', 'logo', 'button', 'badge', 'emoji']):
        return {
            'should_extract': False,
            'reason': '可能是图标/logo',
            'confidence': 80
        }
    
    # ====== 2. 检查内容类型关键词 ======
    matched_keywords = []
    for kw in CONTENT_KEYWORDS:
        if kw in alt_lower or kw in url_lower:
            matched_keywords.append(kw)
    
    if matched_keywords:
        return {
            'should_extract': True,
            'reason': f'有价值的内容图 ({", ".join(matched_keywords[:3])})',
            'confidence': 90
        }
    
    # ====== 3. 基于位置/上下文的启发式判断 ======
    
    # 微信文章的前2张通常是封面/头图，不太可能是内容图
    if idx <= 2 and total_images > 5:
        return {
            'should_extract': False,
            'reason': '文章前几张通常是封面/头图',
            'confidence': 60
        }
    
    # 如果alt是简单的"图片"但位置靠后，可能是内容图
    if alt in ['图片', 'image', 'img', '']:
        # 判断依据：文章中后段的"图片"更可能是内容图
        if idx > 3 and total_images > 5:
            return {
                'should_extract': True,  # 改为提取，因为可能是正文配图
                'reason': f'文章正文中的配图 (位置 {idx}/{total_images})',
                'confidence': 55
            }
        else:
            return {
                'should_extract': False,
                'reason': '前段的"图片"通常是封面/装饰',
                'confidence': 60
            }
    
    # 如果alt包含数字、技术术语，可能是数据/图表
    if any(c.isdigit() for c in alt) and len(alt) > 5:
        return {
            'should_extract': True,
            'reason': '可能是数据/图表 (包含数字和描述)',
            'confidence': 70
        }
    
    # 如果alt有意义但不匹配任何关键词，建议提取（人工筛选）
    if len(alt) > 3 and alt not in ['图片', 'image', 'img', '']:
        return {
            'should_extract': None,  # 不确定，需要人工判断
            'reason': f'有描述的配图: {alt[:30]}',
            'confidence': 50
        }
    
    # 默认：不确定
    return {
        'should_extract': None,
        'reason': '无法自动判断，建议人工查看',
        'confidence': 50
    }


def select_images(md_file: Path, auto_mode: bool = False) -> List[int]:
    """
    选择性提取图片
    
    Args:
        md_file: Markdown文件路径
        auto_mode: 是否自动模式（不询问用户）
    
    Returns:
        要提取的图片序号列表
    """
    content = md_file.read_text(encoding='utf-8')
    
    # 提取文章正文预览（前2000字符，去掉frontmatter）
    body = re.sub(r'^---[\s\S]*?---', '', content).strip()[:2000]
    
    # 获取所有图片
    images = extract_all_images(content)
    
    if not images:
        print("❌ 文章中没有找到图片")
        return []
    
    print(f"\n📄 文章: {md_file.name}")
    print(f"🖼️  共发现 {len(images)} 张图片\n")
    
    # 分析每张图片
    to_extract = []      # 确定要提取
    uncertain = []       # 不确定
    to_exclude = []      # 确定不提取
    
    for idx, alt, url in images:
        analysis = analyze_image_relevance(idx, alt, url, body, len(images))
        
        item = {
            'idx': idx,
            'alt': alt[:50] + '...' if len(alt) > 50 else alt,
            'url_preview': url[:60] + '...' if len(url) > 60 else url,
            **analysis
        }
        
        if analysis['should_extract'] is True:
            to_extract.append(item)
        elif analysis['should_extract'] is False:
            to_exclude.append(item)
        else:
            uncertain.append(item)
    
    # 显示分析结果
    if to_extract:
        print("=" * 80)
        print(f"✅ 建议提取 ({len(to_extract)} 张):")
        print("=" * 80)
        for item in to_extract:
            print(f"  [{item['idx']}] {item['alt']}")
            print(f"       原因: {item['reason']} (置信度: {item['confidence']}%)")
            print()
    
    if uncertain:
        print("=" * 80)
        print(f"⚠️  需要判断 ({len(uncertain)} 张):")
        print("=" * 80)
        for item in uncertain:
            print(f"  [{item['idx']}] {item['alt']}")
            print(f"       原因: {item['reason']}")
            print()
    
    if to_exclude:
        print("=" * 80)
        print(f"❌ 建议跳过 ({len(to_exclude)} 张):")
        print("=" * 80)
        for item in to_exclude[:5]:  # 只显示前5个
            print(f"  [{item['idx']}] {item['alt']} - {item['reason']}")
        if len(to_exclude) > 5:
            print(f"       ... 还有 {len(to_exclude)-5} 张")
        print()
    
    # 收集结果
    selected = [item['idx'] for item in to_extract]
    
    # 处理不确定的图片
    if uncertain and not auto_mode:
        print("=" * 80)
        print("请指定要包含的不确定图片序号（逗号分隔，或输入all/none）:")
        user_input = input("> ").strip()
        
        if user_input.lower() == 'all':
            selected.extend([item['idx'] for item in uncertain])
        elif user_input.lower() != 'none' and user_input:
            try:
                extra = [int(x.strip()) for x in user_input.split(',')]
                selected.extend(extra)
            except ValueError:
                print("⚠️  输入格式错误，跳过")
    elif uncertain and auto_mode:
        # 自动模式下，跳过不确定的
        print(f"🤖 自动模式: 跳过 {len(uncertain)} 张不确定图片")
    
    return sorted(set(selected))


def download_images(md_file: Path, indices: List[int], output_dir: str = "0_Inbox/image-staging") -> List[Path]:
    """下载指定序号的图片"""
    if not indices:
        print("没有要下载的图片")
        return []
    
    content = md_file.read_text(encoding='utf-8')
    images = extract_all_images(content)
    
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    downloaded = []
    
    print(f"\n📥 开始下载 {len(indices)} 张图片...")
    print("=" * 80)
    
    for idx in indices:
        # 找到对应图片
        img_info = next((img for img in images if img[0] == idx), None)
        if not img_info:
            print(f"⚠️  [{idx}] 未找到")
            continue
        
        _, alt, url = img_info
        ext = '.png' if 'png' in url else '.jpg'
        filename = f"{md_file.stem}_{idx:02d}{ext}"
        filepath = out / filename
        
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 1000:
                filepath.write_bytes(resp.content)
                downloaded.append(filepath)
                size_kb = len(resp.content) // 1024
                print(f"✅ [{idx}] {filename} ({size_kb}KB) - {alt[:30]}...")
            else:
                print(f"❌ [{idx}] 下载失败或文件过小")
        except Exception as e:
            print(f"❌ [{idx}] 错误: {e}")
    
    print("=" * 80)
    print(f"📊 完成: {len(downloaded)}/{len(indices)} 张")
    print(f"📁 保存到: {out.absolute()}")
    
    return downloaded


def verify_downloaded_images(image_paths: List[Path], article_title: str) -> None:
    """
    简单验证下载的图片
    TODO: 可以接入AI视觉分析进一步验证
    """
    if not image_paths:
        return
    
    print("\n🔍 快速验证:")
    print("=" * 80)
    
    for path in image_paths:
        size_kb = path.stat().st_size // 1024
        
        # 简单的大小检查
        if size_kb < 10:
            status = "⚠️  过小，可能是图标/装饰"
        elif size_kb > 500:
            status = "📸 高分辨率，可能是截图/照片"
        else:
            status = "✓ 正常"
        
        print(f"  {path.name}: {size_kb}KB - {status}")
    
    print("\n💡 提示: 你可以查看这些图片，确认是否符合预期")
    print(f"   目录: {image_paths[0].parent}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='AI智能图片提取器')
    parser.add_argument('md_file', help='Markdown文章路径')
    parser.add_argument('--auto', '-a', action='store_true', help='自动模式（不询问）')
    parser.add_argument('--output', '-o', default='0_Inbox/image-staging', help='输出目录')
    parser.add_argument('--indices', '-i', help='直接指定序号（如: 1,3,5）')
    
    args = parser.parse_args()
    
    md_path = Path(args.md_file)
    if not md_path.exists():
        print(f"❌ 文件不存在: {args.md_file}")
        sys.exit(1)
    
    # 如果直接指定序号，跳过分析
    if args.indices:
        indices = [int(x.strip()) for x in args.indices.split(',')]
    else:
        # AI选择性分析
        indices = select_images(md_path, auto_mode=args.auto)
    
    if not indices:
        print("\n没有要提取的图片")
        sys.exit(0)
    
    # 下载
    downloaded = download_images(md_path, indices, args.output)
    
    # 验证
    verify_downloaded_images(downloaded, md_path.stem)


if __name__ == '__main__':
    main()
