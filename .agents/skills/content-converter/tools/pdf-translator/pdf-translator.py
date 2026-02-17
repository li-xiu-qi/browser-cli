# -*- coding: utf-8 -*-
"""
PDF 论文翻译工具
封装 PDFMathTranslate (pdf2zh)，提供简化的论文翻译流程
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
from typing import Optional


def check_pdf2zh() -> bool:
    """检查 pdf2zh 是否已安装"""
    return shutil.which("pdf2zh") is not None


def translate_pdf(
    input_path: str,
    output_dir: Optional[str] = None,
    source_lang: str = "en",
    target_lang: str = "zh",
    service: str = "google",
    threads: int = 4,
    pages: Optional[str] = None,
    keep_dual: bool = False,
) -> str:
    """
    翻译单个 PDF 文件
    
    Args:
        input_path: 输入 PDF 文件路径
        output_dir: 输出目录（默认与输入文件同目录）
        source_lang: 源语言代码（默认 en）
        target_lang: 目标语言代码（默认 zh）
        service: 翻译服务（google/deepl/openai/azure/tencent）
        threads: 线程数（默认 4）
        pages: 指定页码范围（如 "1-10"）
        keep_dual: 是否保留双语对照版（默认删除）
    
    Returns:
        翻译后的中文 PDF 文件路径
    """
    if not check_pdf2zh():
        raise RuntimeError("pdf2zh 未安装，请先运行: uv tool install pdf2zh")
    
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"文件不存在: {input_path}")
    
    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # 构建 pdf2zh 命令
    cmd = [
        "pdf2zh",
        str(input_path),
        "-o", str(output_dir),
        "-li", source_lang,
        "-lo", target_lang,
        "-s", service,
        "-t", str(threads),
    ]
    
    if pages:
        cmd.extend(["-p", pages])
    
    print(f"开始翻译: {input_path.name}")
    print(f"输出目录: {output_dir}")
    print(f"翻译服务: {service}")
    
    # 执行翻译
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"翻译失败: {result.stderr}", file=sys.stderr)
        raise RuntimeError(f"pdf2zh 执行失败: {result.stderr}")
    
    # 处理输出文件
    base_name = input_path.stem
    mono_file = output_dir / f"{base_name}-mono.pdf"
    dual_file = output_dir / f"{base_name}-dual.pdf"
    target_file = output_dir / f"{base_name}-zh.pdf"
    
    # 重命名 mono 版本为 -zh.pdf
    if mono_file.exists():
        if target_file.exists():
            target_file.unlink()
        mono_file.rename(target_file)
        print(f"✓ 生成中文版本: {target_file.name}")
    else:
        raise FileNotFoundError(f"未找到翻译输出文件: {mono_file}")
    
    # 保留 dual 版本（默认保留）
    if dual_file.exists():
        print(f"✓ 双语对照版本: {dual_file.name}")
    
    return str(target_file)


def batch_translate(
    input_dir: str,
    output_dir: Optional[str] = None,
    source_lang: str = "en",
    target_lang: str = "zh",
    service: str = "google",
    threads: int = 4,
    keep_dual: bool = False,
) -> list:
    """
    批量翻译目录下的所有 PDF 文件
    
    Returns:
        翻译成功的文件路径列表
    """
    input_dir = Path(input_dir).resolve()
    if not input_dir.exists():
        raise FileNotFoundError(f"目录不存在: {input_dir}")
    
    pdf_files = list(input_dir.glob("*.pdf"))
    # 排除已翻译的文件（避免重复翻译）
    pdf_files = [f for f in pdf_files if not f.name.endswith("-zh.pdf")]
    
    if not pdf_files:
        print(f"目录下没有需要翻译的 PDF 文件: {input_dir}")
        return []
    
    print(f"找到 {len(pdf_files)} 个 PDF 文件待翻译")
    
    results = []
    for pdf_file in pdf_files:
        try:
            result = translate_pdf(
                str(pdf_file),
                output_dir=output_dir,
                source_lang=source_lang,
                target_lang=target_lang,
                service=service,
                threads=threads,
                keep_dual=keep_dual,
            )
            results.append(result)
            print(f"✓ 完成: {pdf_file.name}\n")
        except Exception as e:
            print(f"✗ 失败: {pdf_file.name} - {e}\n", file=sys.stderr)
    
    print(f"批量翻译完成: {len(results)}/{len(pdf_files)} 个文件成功")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="PDF 论文翻译工具 - 基于 PDFMathTranslate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 翻译单个文件
  python pdf-translator.py "paper.pdf"
  
  # 翻译并指定输出目录
  python pdf-translator.py "paper.pdf" -o "./translated/"
  
  # 使用 DeepL 翻译
  python pdf-translator.py "paper.pdf" -s deepl
  
  # 只翻译前 10 页
  python pdf-translator.py "paper.pdf" -p "1-10"
  
  # 批量翻译整个目录
  python pdf-translator.py --batch "./papers/"
        """
    )
    
    parser.add_argument("input", help="输入 PDF 文件或目录路径")
    parser.add_argument("-o", "--output", help="输出目录（默认与输入同目录）")
    parser.add_argument("-li", "--lang-in", default="en", help="源语言代码（默认: en）")
    parser.add_argument("-lo", "--lang-out", default="zh", help="目标语言代码（默认: zh）")
    parser.add_argument("-s", "--service", default="google", 
                        choices=["google", "deepl", "openai", "azure", "tencent"],
                        help="翻译服务（默认: google）")
    parser.add_argument("-t", "--threads", type=int, default=4, help="线程数（默认: 4）")
    parser.add_argument("-p", "--pages", help="页码范围（如: 1-10）")
    parser.add_argument("--batch", action="store_true", help="批量翻译模式（输入为目录）")
    parser.add_argument("--remove-dual", action="store_true", help="删除双语对照版（默认保留）")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    
    args = parser.parse_args()
    
    try:
        if args.batch:
            # 批量翻译
            results = batch_translate(
                args.input,
                output_dir=args.output,
                source_lang=args.lang_in,
                target_lang=args.lang_out,
                service=args.service,
                threads=args.threads,
                keep_dual=not args.remove_dual,
            )
            sys.exit(0 if results else 1)
        else:
            # 单个文件翻译
            result = translate_pdf(
                args.input,
                output_dir=args.output,
                source_lang=args.lang_in,
                target_lang=args.lang_out,
                service=args.service,
                threads=args.threads,
                pages=args.pages,
                keep_dual=not args.remove_dual,
            )
            print(f"\n✓ 翻译完成: {result}")
            sys.exit(0)
    
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n用户取消操作", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
