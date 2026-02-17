#!/usr/bin/env python3
"""
SRT字幕转Markdown文稿工具（增强版）
支持递归处理的文件命名（如：【章节】_视频名.srt）

使用方式:
1. 批量转换: python convert_srt_to_md.py
2. 指定目录: python convert_srt_to_md.py --input-dir subtitles --output-dir transcripts
3. 自定义课程名: python convert_srt_to_md.py --course-name "黄执中：说服高手实战营"
"""

import os
import re
import argparse
from pathlib import Path


def parse_srt_file(srt_path: str) -> list[str]:
    """解析SRT文件，返回文本段落列表"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按空行分割成块
    blocks = re.split(r'\n\s*\n', content.strip())

    texts = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        # 第一行是序号，第二行是时间戳，后面是文本内容
        text_lines = lines[2:]

        # 过滤掉"此字幕由AI自动生成"等元信息
        text = '\n'.join(text_lines).strip()
        if text and '此字幕由AI自动生成' not in text:
            texts.append(text)

    return texts


def smart_paragraphs(texts: list[str]) -> list[str]:
    """
    智能分段：将短句组合成段落
    - 根据标点符号判断句子结束
    - 适当合并，形成可读段落
    """
    # 先合并所有文本
    full_text = ''.join(texts)

    # 按照自然句结束符分割
    sentences = re.split(r'([。！？…]+)', full_text)

    # 重新组合句子
    result = []
    current_para = ''
    char_count = 0

    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i]
        punct = sentences[i + 1] if i + 1 < len(sentences) else ''

        current_para += sentence + punct
        char_count += len(sentence + punct)

        # 当段落达到一定长度时换行（300字左右）
        if char_count >= 300:
            result.append(current_para.strip())
            current_para = ''
            char_count = 0

    # 添加最后一段
    if current_para.strip():
        result.append(current_para.strip())

    return result if result else [full_text]


def extract_title_from_filename(filename: str) -> tuple[str, str]:
        """
        从文件名提取标题和章节信息
        支持格式: 【章节】_视频名.srt 或 视频名.srt
        返回: (章节前缀, 视频标题)
        """
        # 移除.srt后缀
        name = filename.replace('.srt', '')

        # 检查是否有章节前缀格式: 【章节】_视频名
        match = re.match(r'^(.+?)_(.+)$', name)
        if match:
            prefix = match.group(1)
            title = match.group(2)
            # 清理前缀中的特殊字符
            prefix = prefix.replace('【', '').replace('】', '').strip()
            return prefix, title

        return '', name


def convert_srt_to_md(srt_path: str, output_dir: str = 'transcripts', course_name: str = '') -> str:
    """
    将单个SRT文件转换为Markdown

    Args:
        srt_path: SRT文件路径
        output_dir: 输出目录
        course_name: 课程名称（用于Markdown头部）
    """
    srt_file = Path(srt_path)

    # 提取章节和视频标题
    prefix, video_title = extract_title_from_filename(srt_file.stem)

    # 构建Markdown标题
    if prefix:
        display_title = f"{prefix} - {video_title}"
    else:
        display_title = video_title

    # 构建输出路径
    md_file = Path(output_dir) / srt_file.name.replace('.srt', '.md')
    md_file.parent.mkdir(parents=True, exist_ok=True)

    # 解析SRT
    texts = parse_srt_file(srt_path)

    # 智能分段
    paragraphs = smart_paragraphs(texts)

    # 构建Markdown内容
    if course_name:
        header = f"""# {display_title}

> {course_name} - 课程文稿
> 来源：百度网盘字幕自动转换

---

"""
    else:
        header = f"""# {display_title}

> 课程文稿
> 来源：百度网盘字幕自动转换

---

"""

    md_content = header + '\n\n'.join(paragraphs) + "\n\n---\n\n*本文稿由AI字幕自动生成，仅供学习参考*\n"

    # 写入文件
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    return str(md_file)


def batch_convert(subtitles_dir: str = 'subtitles',
                  transcripts_dir: str = 'transcripts',
                  course_name: str = '') -> list[str]:
    """
    批量转换目录下的所有SRT文件为Markdown

    Args:
        subtitles_dir: 字幕目录
        transcripts_dir: 文稿输出目录
        course_name: 课程名称
    """
    subtitles_path = Path(subtitles_dir)

    if not subtitles_path.exists():
        print(f'❌ 目录不存在: {subtitles_dir}')
        return []

    srt_files = sorted(subtitles_path.glob('*.srt'))

    if not srt_files:
        print(f'⚠️ 未找到SRT文件: {subtitles_dir}')
        return []

    print(f'📝 找到 {len(srt_files)} 个字幕文件，开始转换为Markdown...\n')

    converted = []
    for i, srt_file in enumerate(srt_files, 1):
        print(f'[{i}/{len(srt_files)}] 转换: {srt_file.name}')
        md_path = convert_srt_to_md(str(srt_file), transcripts_dir, course_name)
        converted.append(md_path)
        print(f'    ✅ 已保存: {md_path}')

    print(f'\n✨ 全部完成！共转换 {len(converted)} 个文件')
    print(f'📁 Markdown文稿保存在: {transcripts_dir}/')

    return converted


def main():
    parser = argparse.ArgumentParser(description='SRT字幕转Markdown文稿')
    parser.add_argument('--input-dir', default='subtitles', help='字幕文件目录')
    parser.add_argument('--output-dir', default='transcripts', help='文稿输出目录')
    parser.add_argument('--course-name', default='', help='课程名称（用于文档头部）')

    args = parser.parse_args()

    print("=" * 70)
    print("SRT字幕转Markdown工具")
    print("=" * 70)
    if args.course_name:
        print(f"课程名称: {args.course_name}")
    print(f"输入目录: {args.input_dir}")
    print(f"输出目录: {args.output_dir}")
    print("=" * 70)
    print()

    batch_convert(args.input_dir, args.output_dir, args.course_name)


if __name__ == '__main__':
    main()
