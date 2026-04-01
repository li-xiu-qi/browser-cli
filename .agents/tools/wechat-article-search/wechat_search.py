#!/usr/bin/env python3
"""兼容入口：保留旧脚本名，聚合旧的文章搜索与图片提取 CLI。"""
import argparse
import json
import sys

from wechat_client import WechatClient


def cmd_login(args):
    client = WechatClient()
    return 0 if client.login(headless=args.headless) else 1


def cmd_search(args):
    client = WechatClient()
    if not client.token:
        print("⚠️ 未登录，请先运行: python wechat_search.py login")
        return 1
    articles = client.search_articles(args.query, args.count)
    if not articles:
        print("❌ 未找到文章")
        return 1
    print("\n📋 搜索结果:\n")
    for i, art in enumerate(articles, 1):
        print(f"{i}. {art.title}")
        print(f"   公众号: {art.nickname}")
        print(f"   作者: {art.author}")
        print(f"   时间: {art.create_time}")
        print(f"   链接: {art.url}")
        if art.cover_url:
            print(f"   封面: {art.cover_url}")
        print()
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump([{
                'title': a.title,
                'url': a.url,
                'nickname': a.nickname,
                'author': a.author,
                'digest': a.digest,
                'cover_url': a.cover_url,
            } for a in articles], f, ensure_ascii=False, indent=2)
        print(f"✅ 结果已保存: {args.output}")
    return 0


def cmd_search_biz(args):
    client = WechatClient()
    if not client.token:
        print("⚠️ 未登录，请先运行: python wechat_search.py login")
        return 1
    accounts = client.search_accounts(args.query, args.count, args.begin)
    if not accounts:
        print("❌ 未找到公众号")
        return 1
    print("\n📋 公众号搜索结果:\n")
    for i, account in enumerate(accounts, 1):
        print(f"{i}. {account.nickname}")
        print(f"   fakeid: {account.fakeid}")
        print(f"   alias: {account.alias or '-'}")
        print(f"   service_type: {account.service_type}")
        print(f"   verify_status: {account.verify_status}")
        if account.signature:
            print(f"   signature: {account.signature}")
        print()
    return 0


def cmd_list_biz(args):
    client = WechatClient()
    if not client.token:
        print("⚠️ 未登录，请先运行: python wechat_search.py login")
        return 1
    payload = client.list_account_articles(args.fakeid, args.count, args.begin, args.query)
    if not payload:
        print("❌ 获取文章列表失败")
        return 1
    print("\n📋 文章列表:\n")
    print(f"   total_count: {payload['total_count']}")
    print(f"   publish_count: {payload['publish_count']}")
    print(f"   masssend_count: {payload['masssend_count']}\n")
    for i, art in enumerate(payload['articles'], 1):
        print(f"{i}. {art.title}")
        print(f"   作者: {art.author or '-'}")
        print(f"   时间: {art.create_time}")
        print(f"   链接: {art.url}")
        print()
    return 0


def cmd_extract(args):
    client = WechatClient()
    images = client.extract_images_from_article(args.url)
    if not images:
        print("❌ 未找到图片")
        return 1
    print(f"\n📷 找到 {len(images)} 张图片:\n")
    for i, img in enumerate(images[:20], 1):
        print(f"{i}. {img[:80]}...")
    if len(images) > 20:
        print(f"... 还有 {len(images) - 20} 张")
    if args.download:
        client.download_images_to_staging(images, args.prefix or "")
    return 0


def main():
    parser = argparse.ArgumentParser(description="微信公众号文章搜索工具（兼容入口）")
    sub = parser.add_subparsers(dest='cmd', help='命令')

    login_cmd = sub.add_parser('login', help='浏览器登录')
    login_cmd.add_argument('--headless', action='store_true', help='无头模式')
    login_cmd.set_defaults(func=cmd_login)

    search_cmd = sub.add_parser('search', help='搜索文章')
    search_cmd.add_argument('query', help='搜索关键词')
    search_cmd.add_argument('-n', '--count', type=int, default=10, help='返回数量')
    search_cmd.add_argument('-o', '--output', help='保存结果到文件')
    search_cmd.set_defaults(func=cmd_search)

    search_biz_cmd = sub.add_parser('search-biz', help='搜索公众号账号')
    search_biz_cmd.add_argument('query', help='公众号名称关键词')
    search_biz_cmd.add_argument('-n', '--count', type=int, default=5, help='返回数量')
    search_biz_cmd.add_argument('-b', '--begin', type=int, default=0, help='分页起点')
    search_biz_cmd.set_defaults(func=cmd_search_biz)

    list_biz_cmd = sub.add_parser('list-biz', help='按 fakeid 列公众号文章')
    list_biz_cmd.add_argument('fakeid', help='公众号 fakeid')
    list_biz_cmd.add_argument('-n', '--count', type=int, default=5, help='每页数量')
    list_biz_cmd.add_argument('-b', '--begin', type=int, default=0, help='分页起点')
    list_biz_cmd.add_argument('-q', '--query', default='', help='按关键词过滤')
    list_biz_cmd.set_defaults(func=cmd_list_biz)

    extract_cmd = sub.add_parser('extract', help='提取文章图片')
    extract_cmd.add_argument('url', help='文章URL')
    extract_cmd.add_argument('--download', '-d', action='store_true', help='下载到暂存区')
    extract_cmd.add_argument('--prefix', '-p', help='文件名前缀')
    extract_cmd.set_defaults(func=cmd_extract)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
