#!/usr/bin/env python3
"""
电子书整理工具
搜索并整理百度网盘中的电子书文件到统一目录

使用方式:
1. 搜索并分析: python organize_ebooks.py --analyze
2. 执行整理: python organize_ebooks.py --execute --target-dir "/我的资源/3-Resources-资源/领域-电子书"
"""

import requests
import json
import os
import time
import argparse
from collections import defaultdict
from pathlib import Path

# 配置
ACCESS_TOKEN = "123.fe97bdb74eb2238a360649ba4e640f3b.YCnmz8Y2wF3Egn4nxS-K8j4cR-yblsFlhbG8p0A.xyMOUA"
BOOK_EXTENSIONS = ['.pdf', '.epub', '.mobi', '.azw3', '.txt', '.djvu']

# 排除关键词（非电子书）
EXCLUDE_KEYWORDS = [
    # 课件与教学资料
    '课件', 'ppt', '教案', '讲义', '教学大纲', '课程设计', '实验报告',
    '第x章', '第几章', 'chapter', '习题', '课后题', '答案', '解析',
    '复习', '补考', '考试', '试卷', '考题', '题库', '模拟题', '真题',
    '作业', '实验', '实习', '实训', '课程设计', '毕业设计', '论文', '开题',
    # 申报与表格
    '申报', '申报书', '申请表', '报名表', '登记表', '报名表', '申请表',
    '认定', '评定', '评审', '评估', '考核', '检查', '自检', '验收',
    '附件', '证明', '证书', '奖状', '荣誉', '称号',
    # 参考资料
    '参考', '手册', '指南', '说明书', '使用说明', '操作手册', 'api文档',
    '命令速查', 'cheatsheet', 'reference', '速查卡',
    # 报告与文档
    '报告', '总结', '汇报', '简报', '通报', '公告', '通知', '文件',
    '规范', '规定', '制度', '办法', '细则', '条例', '章程', '协议', '合同',
    # 其他非书籍
    '成绩单', '成绩单', '简历', 'cv', '简历模板', '模板', '素材', '样例', '示例',
]

# 电子书正面特征（书名常见特征）
BOOK_POSITIVE_INDICATORS = [
    '著', '作者', '编', '主编', '译', '译本', '原版', '中文版', '英文版',
    '出版社', '出版', '第x版', '第x卷', '上下册', '上册', '下册', '全套',
    '经典', '名著', ' bestseller', '畅销书',
]

# 券商研报识别关键词
REPORT_KEYWORDS = {
    # 报告类型
    '深度报告', '公司深度', '行业深度', '公司研究', '行业研究', '专题报告',
    '跟踪报告', '点评报告', '研报', '研究报告', '证券研究',
    # 券商名称
    '华西证券', '中信证券', '中信建投', '中金公司', '国泰君安', '海通证券',
    '招商证券', '申万宏源', '广发证券', '华泰证券', '兴业证券', '安信证券',
    '光大证券', '平安证券', '国信证券', '东方证券', '长江证券', '方正证券',
    # 页面数特征（如"-35页"、"46页"）
    '-20页', '-25页', '-30页', '-35页', '-40页', '-45页', '-50页',
    '-28页', '-29页', '-30页', '-31页', '-32页', '-33页', '-34页',
    # 日期特征（如"-202308"、"-220222"）
}

# 真正的深度学习/AI技术书籍（用于区分券商研报）
TRUE_AI_BOOKS = [
    '动手学', '算法', '原理', '实战', '入门', '教程', '基础', '框架',
    'pytorch', 'tensorflow', '神经网络', '模型', '识别', '处理',
    '计算机视觉', '自然语言处理', '知识图谱', '面试', '八股',
]

# 分类规则（按优先级排序，先匹配的优先）
BOOK_CATEGORIES = {
    '券商研报': list(REPORT_KEYWORDS),
    '编程开发': ['python', 'java', 'go', 'rust', 'javascript', '编程', '代码', '开发', '架构', '测试', '算法', '数据结构', '软件工程', '设计模式', 'clean code', '重构', 'git', 'linux', 'docker', 'kubernetes', 'k8s', '微服务', 'web开发', '前端', '后端', '数据库', 'mysql', 'redis', 'mongodb', 'nginx', 'spring', 'django', 'flask', 'vue', 'react', 'angular', 'node.js', 'cpp', 'c++', 'c语言', 'rust', 'swift', 'kotlin', 'php', 'ruby', 'perl', 'shell', 'bash', '运维', 'devops', 'ci/cd', '自动化', '面试', 'leetcode', '程序员', '技术'],
    'AI与数据': ['ai', '人工智能', '机器学习', '深度学习', '数据', '大模型', 'nlp', 'cv', '神经网络', '自然语言处理', '计算机视觉', '图像处理', '语音识别', '推荐系统', '数据挖掘', '数据分析', '数据科学', '大数据', 'tensorflow', 'pytorch', 'pandas', 'numpy', 'sklearn', '机器学习实战', '强化学习', '图神经网络', 'transformer', 'bert', 'gpt', 'llm', 'langchain', 'rag', 'agent', '提示词', 'prompt', 'embedding', '向量'],
    '软技能': ['沟通', '表达', '演讲', '写作', '时间管理', '效率', '思考', '思维', '心理学', '心流', '谈判', '说服', '影响力', '情商', '情绪', '压力', '焦虑', '冥想', '专注力', '注意力', '阅读', '笔记', '记忆', '学习方法', '费曼', '刻意练习', '习惯', '自律', '拖延', '目标管理', '执行力', '决策', '问题解决', '批判性思维', '逻辑思维', '创新思维', '创造力', '灵感', '洞察', '同理心', '倾听', '反馈', '冲突', '协作'],
    '商业管理': ['商业', '管理', 'mba', '领导力', '团队', '创业', '产品', '运营', '营销', '品牌', '战略', '组织', '企业文化', '人力资源', 'hr', '招聘', '绩效', '薪酬', '财务', '投资', '理财', '股权', '融资', '商业模式', '商业分析', '市场调研', '用户研究', '产品经理', '项目管理', '敏捷', 'scrum', 'okr', 'kpi', '增长', '获客', '留存', '转化', '销售', '客户', '服务', '供应链', '生产', '质量', '流程', '变革', '创新', '竞争', '市场', '行业', '趋势', '机会'],
    '个人成长': ['成长', '学习', '习惯', '自律', '认知', '心智', '情绪', '人际关系', '沟通的方法', '人生', '职业规划', '自我提升', '自我认知', '自信', '勇气', '行动', '坚持', '毅力', '心态', '格局', '视野', '智慧', '成熟', '幸福', '快乐', '满足', '意义', '价值', '人生哲学', '生活', '工作', '平衡', '健康', '运动', '饮食', '睡眠', '精力管理', '人际关系', '社交', '人脉', '圈层', '家庭', '亲子', '教育', '爱情', '婚姻', '恋爱', '情感'],
    '哲学社科': ['哲学', '逻辑', '社会学', '经济学', '历史', '文化', '人类学', '政治学', '法学', '伦理学', '美学', '宗教', '信仰', '世界观', '人生观', '价值观', '辩证法', '唯物主义', '唯心主义', '存在主义', '功利主义', '自由主义', '保守主义', '社会主义', '资本主义', '马克思主义', '凯恩斯', '哈耶克', '亚当·斯密', '马克思', '尼采', '康德', '黑格尔', '海德格尔', '维特根斯坦', '罗素', '福柯', '社会学', '人类学', '考古学', '民俗学', '心理学', '社会心理学', '认知科学', '行为经济学', '博弈论', '复杂系统', '网络科学'],
    '文学与传记': ['文学', '小说', '散文', '诗歌', '戏剧', '名著', '经典', '作家', '诗人', '诺贝尔文学奖', '茅盾文学奖', '红楼梦', '西游记', '水浒传', '三国演义', '金庸', '古龙', '琼瑶', '张爱玲', '鲁迅', '老舍', '巴金', '茅盾', '沈从文', '钱钟书', '余华', '莫言', '刘慈欣', '三体', '科幻', '奇幻', '悬疑', '推理', '侦探', '恐怖', '武侠', '言情', '都市', '历史小说', '传记', '自传', '回忆录', '人物', '名人', '领袖', '企业家', '科学家', '艺术家'],
    '科技与工程': ['科技', '工程', '电子', '电路', '信号', '通信', '网络', '物联网', '嵌入式', '单片机', 'fpga', '芯片', '半导体', '硬件', '机械', '自动化', '控制', '系统', '机器人', '无人机', '3d打印', '新能源', '电池', '光伏', '材料', '纳米', '生物', '医疗', '健康', '航空航天', '汽车', '交通', '建筑', '土木', '化工', '能源', '环境', '可持续发展'],
    '数学与科学': ['数学', '高等数学', '线性代数', '概率论', '统计学', '微积分', '离散数学', '图论', '数论', '密码学', '物理', '力学', '电磁学', '光学', '热力学', '量子', '相对论', '宇宙', '天文', '化学', '生物', '生命科学', '基因', 'dna', '进化', '生态', '地球科学', '地质', '气象', '海洋', '地理', '地图', 'gis'],
}


def search_files(keyword, num=100):
    """搜索文件"""
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    params = {
        "method": "search",
        "access_token": ACCESS_TOKEN,
        "key": keyword,
        "num": num
    }

    try:
        r = requests.get(url, params=params, timeout=120)
        data = r.json()
        if data.get("errno") == 0:
            return data.get("list", [])
    except Exception as e:
        print(f"  搜索出错: {e}")
    return []


def is_book(filename):
    """检查是否为电子书"""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in BOOK_EXTENSIONS:
        return False

    # 检查排除关键词
    name_lower = filename.lower()
    for keyword in EXCLUDE_KEYWORDS:
        if keyword.lower() in name_lower:
            return False

    return True


def get_file_size(size):
    """格式化文件大小"""
    if size < 1024 * 1024:
        return f"{size/1024:.1f}KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size/1024/1024:.1f}MB"
    else:
        return f"{size/1024/1024/1024:.2f}GB"


def is_true_ai_book(filename):
    """判断是否为真正的AI技术书籍（而非券商研报）"""
    name_lower = filename.lower()

    # 如果包含券商研报特征，先排除
    for keyword in REPORT_KEYWORDS:
        if keyword in name_lower:
            return False

    # 检查是否有真正的AI技术书籍特征
    for indicator in TRUE_AI_BOOKS:
        if indicator in name_lower:
            return True

    return False


def categorize_book(filename):
    """根据文件名判断书籍分类"""
    name_lower = filename.lower()

    # 先检查是否为券商研报（优先级最高）
    for keyword in REPORT_KEYWORDS:
        if keyword in name_lower:
            return '券商研报'

    # 检查AI与数据分类（需要区分真正的AI书籍和券商研报）
    ai_keywords = BOOK_CATEGORIES.get('AI与数据', [])
    for keyword in ai_keywords:
        if keyword in name_lower:
            # 如果包含"深度学习"，需要进一步判断
            if '深度学习' in name_lower or '深度' in name_lower:
                if is_true_ai_book(filename):
                    return 'AI与数据'
                else:
                    # 可能是券商研报，跳过AI分类
                    continue
            else:
                return 'AI与数据'

    # 其他分类
    for category, keywords in BOOK_CATEGORIES.items():
        if category == 'AI与数据':  # 已处理过
            continue
        if category == '券商研报':  # 已处理过
            continue
        for keyword in keywords:
            if keyword in name_lower:
                return category

    return '其他'


def analyze_books(books):
    """分析书籍分布"""
    if not books:
        print("\n❌ 未找到电子书")
        return

    print(f"\n📚 共找到 {len(books)} 本电子书")
    print("=" * 70)

    # 按格式统计
    format_stats = defaultdict(lambda: {'count': 0, 'size': 0})
    for book in books:
        ext = os.path.splitext(book['filename'])[1].lower()
        format_stats[ext]['count'] += 1
        format_stats[ext]['size'] += book['size']

    print("\n📊 按格式分布:")
    for ext in sorted(format_stats.keys()):
        stats = format_stats[ext]
        print(f"  {ext:8s}: {stats['count']:3d} 本 ({get_file_size(stats['size'])})")

    # 按分类统计
    category_stats = defaultdict(list)
    for book in books:
        cat = categorize_book(book['filename'])
        category_stats[cat].append(book)

    print("\n📂 按主题分类:")
    for cat in sorted(category_stats.keys()):
        count = len(category_stats[cat])
        print(f"  {cat:12s}: {count:3d} 本")

    # 显示书籍列表
    print("\n📖 书籍列表:")
    print("-" * 70)
    for i, book in enumerate(books[:50], 1):
        cat = categorize_book(book['filename'])
        size = get_file_size(book['size'])
        print(f"  {i:2d}. [{cat:8s}] {book['filename'][:45]:45s} ({size})")

    if len(books) > 50:
        print(f"\n  ... 还有 {len(books) - 50} 本 ...")

    return category_stats


def search_all_books():
    """搜索所有电子书"""
    print("=" * 70)
    print("🔍 正在搜索百度网盘中的电子书...")
    print("=" * 70)

    all_books = []
    seen_ids = set()

    # 按格式搜索
    for ext in BOOK_EXTENSIONS:
        print(f"\n搜索 *{ext} 文件...")
        keyword = ext[1:]  # 去掉点号
        results = search_files(keyword)

        for item in results:
            filename = item.get("server_filename", "")
            if is_book(filename) and item.get("fs_id") not in seen_ids:
                seen_ids.add(item.get("fs_id"))
                all_books.append({
                    'filename': filename,
                    'path': item.get("path"),
                    'size': item.get("size", 0),
                    'fs_id': item.get("fs_id"),
                    'category': categorize_book(filename)
                })

        time.sleep(0.5)

    return all_books


def generate_organize_plan(books, target_base, report_base="/我的资源/3-Resources-资源/资源文件夹/券商研报"):
    """生成整理方案

    Args:
        books: 书籍列表
        target_base: 电子书目标目录
        report_base: 券商研报目标目录
    """
    plan = []

    for book in books:
        cat = book['category']
        # 券商研报单独存放
        if cat == '券商研报':
            target_dir = report_base
        else:
            target_dir = f"{target_base}/{cat}"

        plan.append({
            'source': book['path'],
            'target_dir': target_dir,
            'filename': book['filename'],
            'category': cat
        })

    return plan


def main():
    parser = argparse.ArgumentParser(description='电子书整理工具')
    parser.add_argument('--analyze', action='store_true', help='分析当前电子书分布')
    parser.add_argument('--execute', action='store_true', help='执行整理操作')
    parser.add_argument('--target-dir', default='/我的资源/3-Resources-资源/领域-电子书',
                        help='电子书目标目录')
    parser.add_argument('--report-dir', default='/我的资源/3-Resources-资源/资源文件夹/券商研报',
                        help='券商研报目标目录')

    args = parser.parse_args()

    if not args.analyze and not args.execute:
        parser.print_help()
        return

    # 搜索书籍
    books = search_all_books()

    if not books:
        print("\n❌ 没有找到电子书")
        return

    # 分析
    category_stats = analyze_books(books)

    if args.execute:
        print("\n" + "=" * 70)
        print("📁 整理方案:")
        print(f"  电子书: {args.target_dir}")
        print(f"  券商研报: {args.report_dir}")
        print("=" * 70)

        plan = generate_organize_plan(books, args.target_dir, args.report_dir)

        # 统计分类
        report_count = sum(1 for item in plan if item['category'] == '券商研报')
        book_count = len(plan) - report_count

        print(f"\n📊 整理统计:")
        print(f"  电子书: {book_count} 本")
        print(f"  券商研报: {report_count} 本")

        print("\n整理计划预览 (前20条):")
        for item in plan[:20]:
            target = "研报" if item['category'] == '券商研报' else "书籍"
            print(f"  [{target}] {item['filename'][:40]}")

        if len(plan) > 20:
            print(f"\n  ... 还有 {len(plan) - 20} 本 ...")

        print(f"\n⚠️  实际移动操作需要调用API，建议先手动确认后再执行")
        print(f"💡 可以使用百度网盘网页版按上述分类手动整理")

    print("\n" + "=" * 70)
    print("完成!")
    print("=" * 70)


if __name__ == '__main__':
    main()
