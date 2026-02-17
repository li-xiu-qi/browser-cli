# narrative-service vs 多模态模型对比分析

**文档日期**: 2026-02-05  
**核心问题**: narrative-service和多模态模型有什么区别？多模态模型可以直接读懂图片吗？  
**一句话回答**: 一个是**规则引擎**，一个是**神经网络**，技术路线完全不同。多模态模型确实可以读懂图片。

---

## 一、本质区别

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        两者的本质区别                                      │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  【narrative-service】                         【多模态模型】               │
│                                                                            │
│  基于规则的系统                              基于神经网络的AI              │
│  ┌─────────────────────────┐                ┌─────────────────────────┐   │
│  │ 输入：结构化数据         │                │ 输入：任意模态           │   │
│  │  - 数字表格              │                │  - 图片                 │   │
│  │  - CSV/JSON              │                │  - 文本                 │   │
│  │  - 数据库查询结果         │                │  - 音频                 │   │
│  │                        │                │  - 视频                 │   │
│  │ 处理：                  │                │  处理：                  │   │
│  │  统计算法 → 规则引擎 →   │                │  Transformer神经网络    │   │
│  │  NLG模板                │                │  端到端处理              │   │
│  │                        │                │                        │   │
│  │ 输出：结构化报告         │                │ 输出：自由文本           │   │
│  │  "销售额增长20%..."      │                │  "从图中可以看出..."     │   │
│  └─────────────────────────┘                └─────────────────────────┘   │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 二、技术原理对比

### 2.1 narrative-service：规则+模板

```python
# 核心工作流程

class NarrativeService:
    def generate_report(self, data):
        # Step 1: 统计模式检测（确定性算法）
        trend = self.detect_trend(data)  # 线性回归
        outliers = self.detect_outliers(data)  # IQR方法
        
        # Step 2: 规则匹配
        insights = []
        if trend['direction'] == 'up' and trend['strength'] == 'strong':
            insights.append({
                'type': 'trend',
                'priority': 9,
                'description': '呈现强劲上升趋势'
            })
        
        if outliers:
            insights.append({
                'type': 'outlier',
                'priority': 7,
                'description': f'发现{len(outliers)}个异常点'
            })
        
        # Step 3: NLG模板填充
        template = "本季度{metric}{trend}，{outlier}。建议关注。"
        report = template.format(
            metric='销售额',
            trend=insights[0]['description'],
            outlier=insights[1]['description']
        )
        
        return report

# 特点：
# - 每一步都是确定性的
# - 可解释：知道为什么生成这句话
# - 需要预定义规则和模板
```

### 2.2 多模态模型：神经网络

```python
# 多模态模型（GPT-4V、Claude 3、Gemini）

class MultimodalLLM:
    def analyze(self, input_data):
        # 输入可以是图片、文本、音频等
        
        # 端到端的神经网络处理
        # 内部是Transformer架构（数十亿参数）
        # 没有显式的规则或模板
        
        # 自回归生成文本
        output = self.model.generate(
            input=input_data,
            max_tokens=1000
        )
        
        return output

# 特点：
# - 神经网络内部是黑盒
# - 不可解释：不知道为什么这么说
# - 通用性强：不需要预定义
```

---

## 三、核心能力对比

### 3.1 能否读懂图片？

| 能力 | narrative-service | 多模态模型(GPT-4V) |
|------|-------------------|-------------------|
| **图表图片** |  不能直接读 |  "这是一张柱状图，显示Q1销售额比Q2高30%" |
| **照片** |  不能处理 |  "这是一张会议室照片，有5个人在讨论" |
| **扫描文档** |  不能处理 |  OCR+理解内容 |
| **结构化数据** |  专门处理 |  也能处理 |

**关键区别**:
- narrative-service: 必须输入**结构化数据**（数字、表格）
- 多模态模型: 可以直接输入**图片**，自动理解内容

### 3.2 其他能力对比

| 维度 | narrative-service | 多模态模型 |
|------|-------------------|-----------|
| **输入类型** | 仅限结构化数据 | 图片、文本、音频等 |
| **输出确定性** |  同样输入总是同样输出 |  有随机性，可能不同 |
| **可解释性** |  可追踪每句话的来源 |  黑盒，不可解释 |
| **幻觉风险** |  低（基于统计数据） |  高（可能胡说） |
| **运行成本** |  低（普通CPU） |  高（需要GPU） |
| **部署方式** |  本地部署 | 通常API调用 |
| **定制化** |  可修改规则 |  只能调prompt |
| **通用性** |  只能做数据报告 |  什么任务都能做 |

---

## 四、实际场景对比

### 场景1：分析销售数据

**narrative-service方式**:
```python
# 输入必须是结构化数据
import requests

data = {
    "data": [
        {"month": "1月", "sales": 100},
        {"month": "2月", "sales": 120},
        {"month": "3月", "sales": 90}
    ],
    "metric_columns": ["sales"],
    "time_column": "month"
}

response = requests.post(
    "http://narrative-service:5004/analyze",
    json=data
)

# 输出：
"本季度销售额呈现波动趋势。2月份达到峰值120，3月份下滑至90，
环比下降25%。建议关注3月份销售下滑原因。"
```

**多模态模型方式**:
```python
# 可以直接给截图！
from openai import OpenAI

client = OpenAI()

# 上传销售报表截图
response = client.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "分析这张销售报表"},
            {"type": "image_url", "image_url": {"url": "sales_chart.png"}}
        ]
    }]
)

# 输出：
"从这张柱状图可以看出，该公司Q1销售额呈先升后降趋势。
2月份达到峰值120万，但3月份明显下滑至90万。
值得注意的是，3月份的数据点旁有一个红色标记，可能是异常提醒。
建议深入调查3月份的销售情况..."
```

**对比总结**:
| 方面 | narrative-service | 多模态模型 |
|------|-------------------|-----------|
| 输入 | JSON数据 | 图片截图 |
| 理解图表 |  需要预输入数据 |  直接读图 |
| 发现异常 |  算法检测 |  视觉发现 |
| 输出风格 | 结构化、模板化 | 自然、灵活 |

---

## 五、为什么RATH不用多模态模型？

### 5.1 技术选型考虑

RATH设计时（2020-2022年）多模态模型还不成熟，但也即使现在，两者各有优势：

**narrative-service的优势**:
1. **成本低**: 普通CPU服务器即可运行
2. **确定性强**: 同样的数据总是同样的结论
3. **可解释**: 可以追踪每句话的数据来源
4. **隐私安全**: 数据不出本地，不上传云端
5. **可控**: 可以精确控制输出格式和内容

**多模态模型的劣势**（在数据分析场景）:
1. **幻觉**: 可能编造数据或趋势
2. **成本高**: 调用API费用高，本地部署需要GPU
3. **不可控**: 输出格式不稳定
4. **隐私**: 数据需要上传到云端
5. **解释性**: 无法解释为什么得出某个结论

### 5.2 最佳实践：两者结合

```
推荐架构：

数据 → narrative-service（规则分析） → 结构化洞察
                                      ↓
用户上传图片 → 多模态模型（初步理解） → 图片内容描述
                                      ↓
                              融合 → 综合报告
                                      ↓
                              LLM（润色生成） → 最终输出

分工：
- narrative-service: 精确统计、确保准确
- 多模态模型: 理解图片、提取信息
- LLM: 润色表达、生成自然语言
```

---

## 六、总结

| 问题 | 答案 |
|------|------|
| 多模态模型能读懂图片吗？ |  是的，可以直接理解图片内容 |
| narrative-service能读图片吗？ |  不能，只能处理结构化数据 |
| 哪个更好？ | 取决于场景，两者可以结合使用 |
| RATH为什么不用多模态？ | 成本、确定性、隐私、可解释性考虑 |

### 选择建议

| 场景 | 推荐方案 |
|------|---------|
| 数据安全敏感 | narrative-service本地部署 |
| 用户上传截图分析 | 多模态模型 |
| 需要精确数字 | narrative-service |
| 需要自然语言解释 | 两者结合 |
| 预算有限 | narrative-service |
| 快速原型验证 | 多模态模型API |

---

## 参考

- OpenAI GPT-4V: https://platform.openai.com/docs/guides/vision
- Claude 3 Vision: https://www.anthropic.com/news/claude-3-family
- Google Gemini: https://deepmind.google/technologies/gemini/
