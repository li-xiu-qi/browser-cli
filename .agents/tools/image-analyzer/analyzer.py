#!/usr/bin/env python3
"""
图片描述生成器 - 基于 SiliconFlow VLM
为无多模态能力的 AI 提供图片信息
"""
import os
import sys
import json
import base64
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass, asdict

# API 配置
API_KEY = "sk-tcgyvneoqksdohcvgarkduafhmjvcvcmzcfvspgltookbygk"
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "Qwen/Qwen3-VL-32B-Instruct"


@dataclass
class ImageDescription:
    """图片描述数据结构"""
    description: str           # 详细描述
    caption: str              # 一句话摘要
    tags: list               # 标签列表
    usage_scenarios: list    # 适用场景
    has_watermark: bool      # 是否有水印
    quality: str             # 质量评估 (high/medium/low)
    subject: Optional[str]   # 主体（人物/物品名称）
    style: Optional[str]     # 风格（写实/插画/截图等）


def encode_image(image_path: Path) -> str:
    """将图片转为 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image(image_path: Path) -> Optional[ImageDescription]:
    """
    使用 VLM 分析图片
    
    Args:
        image_path: 图片文件路径
    
    Returns:
        ImageDescription 对象
    """
    if not image_path.exists():
        print(f"❌ 文件不存在: {image_path}")
        return None
    
    print(f"🔍 分析图片: {image_path.name}")
    
    # 编码图片
    try:
        base64_image = encode_image(image_path)
    except Exception as e:
        print(f"❌ 图片编码失败: {e}")
        return None
    
    # 构建请求
    prompt = """请详细分析这张图片，提供以下信息（JSON格式）：

1. description: 详细描述图片内容（100-200字）
2. caption: 一句话摘要（20字以内）
3. tags: 标签列表（5-10个关键词）
4. usage_scenarios: 适用场景（如：文章配图、PPT插图、壁纸等）
5. has_watermark: 是否有水印（true/false）
6. quality: 质量评估（high/medium/low）
7. subject: 主体名称（如人物名、产品名，没有则null）
8. style: 图片风格（写实照片/插画/截图/设计图等）

请严格返回JSON格式，不要包含其他文字。"""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.3
    }
    
    # 发送请求
    try:
        import requests
        
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # 解析 JSON
        try:
            # 清理可能的 markdown 代码块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content.strip())
            
            return ImageDescription(
                description=data.get("description", ""),
                caption=data.get("caption", ""),
                tags=data.get("tags", []),
                usage_scenarios=data.get("usage_scenarios", []),
                has_watermark=data.get("has_watermark", False),
                quality=data.get("quality", "medium"),
                subject=data.get("subject"),
                style=data.get("style")
            )
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败，尝试提取信息: {e}")
            # 返回原始内容作为描述
            return ImageDescription(
                description=content[:500],
                caption=content[:50],
                tags=[],
                usage_scenarios=[],
                has_watermark=False,
                quality="unknown",
                subject=None,
                style=None
            )
            
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        return None


def save_description(image_path: Path, desc: ImageDescription) -> Path:
    """
    保存描述到 JSON 文件
    
    Args:
        image_path: 原图片路径
        desc: 描述对象
    
    Returns:
        JSON 文件路径
    """
    output_path = image_path.parent / f"{image_path.name}.json"
    
    # 添加元信息
    data = asdict(desc)
    data["_meta"] = {
        "image_file": image_path.name,
        "image_path": str(image_path),
        "analyzed_at": import_datetime().now().isoformat(),
        "model": MODEL
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 描述已保存: {output_path.name}")
    return output_path


def import_datetime():
    """延迟导入 datetime"""
    from datetime import datetime
    return datetime


def analyze_single(image_path: str, save: bool = True):
    """分析单张图片"""
    path = Path(image_path)
    
    desc = analyze_image(path)
    if not desc:
        return 1
    
    # 打印结果
    print(f"\n📋 分析结果:")
    print(f"  Caption: {desc.caption}")
    print(f"  Tags: {', '.join(desc.tags)}")
    print(f"  Usage: {', '.join(desc.usage_scenarios)}")
    print(f"  Quality: {desc.quality}")
    print(f"  Watermark: {'Yes' if desc.has_watermark else 'No'}")
    
    if save:
        save_description(path, desc)
    else:
        print(f"\n{json.dumps(asdict(desc), ensure_ascii=False, indent=2)}")
    
    return 0


def analyze_directory(directory: str, pattern: str = "*"):
    """批量分析目录中的图片"""
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"❌ 目录不存在: {directory}")
        return 1
    
    # 支持的图片格式
    extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
    
    images = []
    for ext in extensions:
        images.extend(dir_path.glob(f"{pattern}{ext}"))
        images.extend(dir_path.glob(f"{pattern}{ext.upper()}"))
    
    # 排除已分析的
    to_analyze = [img for img in images if not (img.parent / f"{img.name}.json").exists()]
    
    print(f"📊 找到 {len(images)} 张图片，待分析 {len(to_analyze)} 张\n")
    
    success = 0
    for img in to_analyze:
        if analyze_single(str(img), save=True) == 0:
            success += 1
        print()
    
    print(f"✅ 完成: {success}/{len(to_analyze)} 张")
    return 0


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="图片描述生成器 - 基于 VLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析单张图片
  python analyzer.py image.jpg
  
  # 分析目录（跳过已有描述的）
  python analyzer.py --dir ./images
  
  # 只输出不保存
  python analyzer.py image.jpg --no-save
        """
    )
    
    parser.add_argument("path", nargs="?", help="图片路径或目录")
    parser.add_argument("--dir", "-d", action="store_true", help="批量分析目录")
    parser.add_argument("--no-save", action="store_true", help="不保存，仅输出")
    parser.add_argument("--pattern", default="*", help="文件匹配模式（批量时）")
    
    args = parser.parse_args()
    
    if not args.path:
        parser.print_help()
        return 0
    
    if args.dir:
        return analyze_directory(args.path, args.pattern)
    else:
        return analyze_single(args.path, save=not args.no_save)


if __name__ == "__main__":
    sys.exit(main())
