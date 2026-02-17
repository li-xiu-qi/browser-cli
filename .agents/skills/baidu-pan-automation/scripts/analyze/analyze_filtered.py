#!/usr/bin/env python3
"""
基于第一次搜索结果，分析过滤效果
"""

import re
from collections import defaultdict

# 第一次搜索的原始书籍列表（部分示例）
raw_books = [
    "2018-10-06黄执中《情绪沟通——改变看法与自我认知》ppt .pdf",
    "附件1、职业技能等级认定申报条件.pdf",
    "第4章(FFT).pdf",
    "3_计控考试.pdf",
    "嵌入式复习.pdf",
    "自检补考题.pdf",
    "3.3傅里叶变换.pdf",
    "6.5Z变换基本性质.pdf",
    "3.8 序列的傅里叶变换2.pdf",
    "6.6利用Z变换解差分方程.pdf",
    "5.3拉氏变换的基本性质pdf.pdf",
    "附件1：中国国际大学生创新大赛高教主赛道方案.pdf",
    '附件2：中国国际大学生创新大赛"青年红色筑梦之旅"活动方案.pdf',
    '东油青研科教联发（2025）1号第十九届"挑战杯"大学生课外学术科技作品....pdf',
    "简洁报告单_电气信息工程学院科技发明制作B类基于RAG的油田问答小助手李秀奇申报书.pdf",
    "自动控制原理 (胡寿松) .pdf",
    "过程控制系统（第3版） (齐卫红主编 刘芳园副主编) .pdf",
    "智能化测量控制仪表原理与设计（第3版） (徐爱钧，徐阳编著) .pdf",
    "参照1：关于印发《东北石油大学家庭经济困难学生认定工作实施细则（修订）》的通知.pdf",
    "ReferenceCard.pdf",
    "ReferenceCard.pdf",
    "影响力.pdf",
    "资本论.pdf",
    "用户画像.pdf",
    "Mastering RAG-1.pdf",
    "《算法图解》.pdf",
    "动手学深度学习.pdf",
    "如何阅读一本书.pdf",
    "如何阅读一本书.pdf",
    "人月神话-中文版.pdf",
    "5、弱传播-邹振东.pdf",
    "自然语言处理基础.pdf",
    "计算机视觉 (夏皮罗) .pdf",
    "图表示学习 (汉密尔顿) .pdf",
    "微信背后的产品观 (张小龙).pdf",
    "微信背后的产品观 (张小龙).pdf",
    "笔记的方法 (刘少楠, 刘白光) .pdf",
    "FFmpeg从入门到精通 (刘歧 赵文杰) .pdf",
    "PYTHON自然语言处理中文版 (it-ebooks) .pdf",
    "知识图谱：概念与技术 (肖仰华 等) .pdf",
    "基于深度学习的自然语言处理 ( etc.) .pdf",
    "自然语言处理综论 第2版 (Pdg2Pic etc.) .pdf",
    "大模型应用开发：动手做 AI Agent (黄佳) .pdf",
    "大数据技术原理与应用(第三版) (林子雨) .pdf",
    "DeepSeek提示词工程和落地场景 (AI肖睿团队) .pdf",
    "动手学强化学习 (张伟楠，沈键，俞勇 著) .pdf",
    "销售就是要会提问 (蔡怀东著, 蔡怀东, author) .pdf",
    "费曼学习法（用输出倒逼输入） (尹红心, 李伟).pdf",
    "18、当下的力量（白金版） ([德]埃克哈特·托利).pdf",
]

# 排除关键词
EXCLUDE_KEYWORDS = [
    '课件', 'ppt', '教案', '讲义', '教学大纲', '课程设计', '实验报告',
    '复习', '补考', '考试', '试卷', '考题', '题库', '模拟题', '真题',
    '作业', '实验', '实习', '实训', '毕业设计', '开题',
    '申报', '申报书', '申请表', '报名表', '登记表',
    '认定', '评定', '评审', '评估', '考核', '检查', '自检', '验收',
    '附件', '证明', '证书', '奖状', '荣誉', '称号',
    '参考卡', 'reference', '速查卡', 'cheatsheet',
    '报告单', '通知', '文件', '规范', '规定', '制度', '办法', '细则', '条例',
    '参照',
]

def is_likely_ebook(filename):
    """判断是否为真正的电子书"""
    name_lower = filename.lower()

    # 检查排除关键词
    for keyword in EXCLUDE_KEYWORDS:
        if keyword.lower() in name_lower:
            return False, f"包含排除词: {keyword}"

    # 检查章节模式 (第X章、第X节等)
    if re.search(r'第\d+章', filename) or re.search(r'第[一二三四五六七八九十]+章', filename):
        return False, "疑似课件章节"

    # 检查纯数字前缀 (如 "3_", "5、")
    if re.match(r'^\d+[_、]', filename):
        return False, "疑似章节编号"

    return True, "可能是电子书"


def main():
    print("=" * 70)
    print("电子书过滤分析")
    print("=" * 70)

    kept = []
    filtered = []

    for book in raw_books:
        is_ebook, reason = is_likely_ebook(book)
        if is_ebook:
            kept.append((book, reason))
        else:
            filtered.append((book, reason))

    print(f"\n📊 总计: {len(raw_books)} 个文件")
    print(f"✅ 保留 (可能是电子书): {len(kept)} 个")
    print(f"❌ 过滤 (非电子书): {len(filtered)} 个")

    print("\n" + "=" * 70)
    print("❌ 被过滤的文件 (非电子书):")
    print("=" * 70)
    for book, reason in filtered:
        print(f"  [{reason:20s}] {book}")

    print("\n" + "=" * 70)
    print("✅ 保留的文件 (可能是电子书):")
    print("=" * 70)
    for book, reason in kept:
        print(f"  {book}")

    # 计算过滤比例
    filter_ratio = len(filtered) / len(raw_books) * 100 if raw_books else 0
    print(f"\n📈 过滤比例: {filter_ratio:.1f}%")
    print("=" * 70)


if __name__ == '__main__':
    main()
