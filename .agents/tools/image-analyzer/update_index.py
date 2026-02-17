"""
图片库索引生成器

自动扫描 image-library 目录下的所有图片文件夹，
读取 metadata.json，生成 index.md 预览文件。
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


def find_image_file(folder_path: Path) -> Optional[str]:
    """在文件夹中查找图片文件（支持多种格式）"""
    for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp']:
        img_file = folder_path / f"image{ext}"
        if img_file.exists():
            return f"image{ext}"
    return None


def read_metadata(folder_path: Path) -> Optional[Dict]:
    """读取 metadata.json 文件"""
    meta_file = folder_path / "metadata.json"
    if not meta_file.exists():
        return None

    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def generate_index_entry(folder_name: str, image_file: str, metadata: Dict) -> str:
    """生成单个图片的索引条目"""
    caption = metadata.get('caption', '无标题')
    subject = metadata.get('subject', '未知')
    style = metadata.get('style', '未知')
    tags = metadata.get('tags', [])
    quality = metadata.get('quality', 'unknown')
    has_watermark = metadata.get('has_watermark', False)
    watermark_text = '有' if has_watermark else '无'

    # 取前6个标签显示
    tag_display = ' '.join([f'`{tag}`' for tag in tags[:6]])

    return f"""## {caption}

**文件夹：** [`{folder_name}/`](./{folder_name}/)

![{caption}](./{folder_name}/{image_file})

| 属性 | 内容 |
|------|------|
| **标题** | {caption} |
| **主题** | {subject} |
| **风格** | {style} |
| **标签** | {tag_display} |
| **质量** | {quality} |
| **水印** | {watermark_text} |

---

"""


def generate_index(image_library_path: Path) -> str:
    """生成完整的 index.md 内容"""
    entries = []
    image_count = 0

    # 遍历所有子文件夹
    for item in sorted(image_library_path.iterdir()):
        if not item.is_dir():
            continue

        folder_name = item.name

        # 跳过非图片文件夹（如 .git 等）
        if folder_name.startswith('.'):
            continue

        # 查找图片文件
        image_file = find_image_file(item)
        if not image_file:
            print(f"警告: {folder_name}/ 中未找到图片文件")
            continue

        # 读取元数据
        metadata = read_metadata(item)
        if not metadata:
            print(f"警告: {folder_name}/ 中未找到 metadata.json")
            # 使用默认元数据
            metadata = {
                'caption': folder_name.replace('-', ' ').title(),
                'subject': '未知',
                'style': '未知',
                'tags': [],
                'quality': 'unknown',
                'has_watermark': False
            }

        # 生成条目
        entry = generate_index_entry(folder_name, image_file, metadata)
        entries.append(entry)
        image_count += 1

    # 构建索引头部
    today = datetime.now().strftime('%Y-%m-%d')
    header = f"""# 图片库索引

> 共 {image_count} 张图片 | 最后更新：{today}

---

"""

    # 构建索引底部（使用说明）
    footer = """## 使用说明

### 添加新图片

1. 在 `image-library/` 下新建文件夹，命名格式：`主题名称`
2. 放入图片文件，命名为 `image.png` 或 `image.jpg`
3. 创建 `metadata.json`，包含以下字段：

```json
{
  "description": "图片描述",
  "caption": "图片标题",
  "tags": ["标签1", "标签2"],
  "usage_scenarios": ["使用场景1"],
  "has_watermark": false,
  "quality": "high",
  "subject": "主题",
  "style": "风格"
}
```

4. 运行 `python .agents/tools/image-analyzer/update_index.py` 更新索引

### 更新索引

```bash
# 在仓库根目录运行
python .agents/tools/image-analyzer/update_index.py

# 或指定图片库路径
python .agents/tools/image-analyzer/update_index.py resources/image-library/
```

---

*此文件由脚本自动生成，请勿手动编辑*
"""

    return header + '\n'.join(entries) + footer


def main():
    """主函数"""
    import sys

    # 确定图片库路径
    if len(sys.argv) > 1:
        image_library_path = Path(sys.argv[1])
    else:
        # 默认路径：从脚本位置推导
        # .agents/tools/image-analyzer/ -> resources/image-library/
        script_dir = Path(__file__).parent
        image_library_path = script_dir.parent.parent.parent / "resources" / "image-library"

    if not image_library_path.exists():
        print(f"错误: 图片库路径不存在: {image_library_path}")
        print("请提供正确的路径，例如:")
        print("  python update_index.py resources/image-library/")
        sys.exit(1)

    print(f"扫描图片库: {image_library_path}")

    # 生成索引
    index_content = generate_index(image_library_path)

    # 写入文件
    index_file = image_library_path / "index.md"
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(index_content)

    # 统计信息
    image_count = index_content.count('## ')
    print(f"✅ 索引已生成: {index_file}")
    print(f"   共 {image_count} 张图片")


if __name__ == "__main__":
    main()
