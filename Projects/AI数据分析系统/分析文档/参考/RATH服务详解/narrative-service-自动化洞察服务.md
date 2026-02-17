# RATH narrative-service：自动化洞察服务详解

**服务定位**: 自动生成数据洞察和叙事报告  
**技术栈**: Python + FastAPI + 规则引擎 + NLG  
**默认端口**: 5004  
**所属项目**: [RATH](https://github.com/Kanaries/RATH)

---

## 一、服务概述

### 1.1 什么是 narrative-service？

narrative-service 是 RATH 的"数据讲故事"引擎，能够**自动分析数据并生成人类可读的文字洞察**：

```
┌─────────────────────────────────────────────────────────────┐
│                   narrative-service :5004                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  原始数据                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  销售数据（10万行）                                   │   │
│  │  - 销售额、日期、地区、产品类别                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  narrative-service                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. 模式识别：发现数据中的关键模式                      │   │
│  │    - 趋势（上升/下降）                                │   │
│  │    - 异常（离群点）                                   │   │
│  │    - 对比（地区差异）                                 │   │
│  │    - 分布（集中趋势）                                 │   │
│  │                                                     │   │
│  │ 2. 洞察生成：将模式转为业务洞察                        │   │
│  │    - "华东区销售额同比增长35%"                        │   │
│  │    - "Q3出现明显下滑，需关注"                         │   │
│  │                                                     │   │
│  │ 3. 叙事组织：构建完整故事线                           │   │
│  │    - 开头：总体概况                                   │   │
│  │    - 主体：关键发现                                   │   │
│  │    - 结尾：建议行动                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  自动生成报告                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │   销售数据分析报告                                  │   │
│  │                                                     │   │
│  │  本季度总销售额达到 1,200万，同比增长15%。            │   │
│  │  华东区表现最为突出，贡献了45%的销售额。              │   │
│  │                                                     │   │
│  │  【关键发现】                                         │   │
│  │  1. 电子产品类别增长最快（+35%）                      │   │
│  │  2. 7月份出现异常下滑（-20%），可能与促销活动结束有关  │   │
│  │  3. 新客户获取成本上升30%                            │   │
│  │                                                     │   │
│  │  【建议行动】                                         │   │
│  │  - 增加华东区库存以满足需求                          │   │
│  │  - 分析7月下滑原因，制定挽回策略                     │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心能力

| 能力 | 说明 | 技术 |
|------|------|------|
| **模式识别** | 自动发现趋势、异常、对比 | 统计检验、规则引擎 |
| **洞察生成** | 将数据模式转为业务洞察 | NLG模板、规则推理 |
| **叙事组织** | 结构化组织洞察成故事 | 叙事框架 |
| **多语言** | 支持中英文报告 | i18n |
| **可视化建议** | 推荐合适的图表类型 | 视觉映射规则 |

---

## 二、技术架构

### 2.1 项目结构

```
narrative-service/
├── main.py                 # FastAPI 入口
├── models.py              # Pydantic 模型
├── requirements.txt       # 依赖
├── Dockerfile            # 容器定义
├── pattern_detection/    # 模式检测
│   ├── __init__.py
│   ├── trend.py          # 趋势检测
│   ├── outlier.py        # 异常检测
│   ├── comparison.py     # 对比分析
│   └── distribution.py   # 分布分析
├── insight_generation/   # 洞察生成
│   ├── __init__.py
│   ├── generator.py      # 洞察生成器
│   ├── templates.py      # NLG模板
│   └── rules.py          # 业务规则
├── narrative_building/   # 叙事构建
│   ├── __init__.py
│   ├── structure.py      # 叙事结构
│   └── ranking.py        # 洞察排序
└── visualization/        # 可视化建议
    ├── __init__.py
    └── recommender.py    # 图表推荐
```

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                  narrative-service :5004                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FastAPI Layer                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ POST /analyze            # 分析数据生成报告         │   │
│  │ POST /patterns           # 仅检测模式               │   │
│  │ POST /insights           # 生成单个洞察             │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  Pattern Detection Layer                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Trend    │ │ Outlier  │ │ Comparison│ │Distribution│     │
│  │ Detector │ │ Detector │ │ Detector │ │ Detector │      │
│  │          │ │          │ │          │ │          │      │
│  │ 趋势检测 │ │ 异常检测 │ │ 对比分析 │ │ 分布分析 │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                           ↓                                  │
│  Insight Generation                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 模式 → 业务洞察转换                                   │   │
│  │ "销售额上升" → "本季度销售额表现强劲"                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  Narrative Building                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 开头：总体概况（KPI）                                │   │
│  │ 主体：Top 5 关键发现                                 │   │
│  │ 结尾：行动建议                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、模式检测层

### 3.1 趋势检测

```python
# pattern_detection/trend.py
import numpy as np
import pandas as pd
from scipy import stats
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class TrendPattern:
    """趋势模式"""
    type: str  # "up", "down", "flat"
    strength: str  # "strong", "moderate", "weak"
    start_value: float
    end_value: float
    change_percent: float
    confidence: float  # 置信度
    description: str

class TrendDetector:
    """趋势检测器"""
    
    def __init__(self, min_change_percent: float = 0.05):
        self.min_change_percent = min_change_percent  # 最小变化阈值5%
    
    def detect(self, series: pd.Series, time_col: pd.Series = None) -> List[TrendPattern]:
        """
        检测时间序列趋势
        
        Args:
            series: 数值序列
            time_col: 时间列（可选，默认用索引）
        
        Returns:
            趋势模式列表
        """
        patterns = []
        
        # 1. 整体趋势（线性回归）
        x = np.arange(len(series))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, series)
        
        start_val = series.iloc[0]
        end_val = series.iloc[-1]
        change_pct = (end_val - start_val) / abs(start_val) if start_val != 0 else 0
        
        # 判断趋势类型
        if abs(change_pct) < self.min_change_percent:
            trend_type = "flat"
        elif change_pct > 0:
            trend_type = "up"
        else:
            trend_type = "down"
        
        # 判断强度
        if abs(r_value) > 0.7:
            strength = "strong"
        elif abs(r_value) > 0.4:
            strength = "moderate"
        else:
            strength = "weak"
        
        # 生成描述
        description = self._generate_description(
            trend_type, strength, change_pct, series
        )
        
        patterns.append(TrendPattern(
            type=trend_type,
            strength=strength,
            start_value=start_val,
            end_value=end_val,
            change_percent=change_pct,
            confidence=abs(r_value),
            description=description
        ))
        
        # 2. 分段趋势（检测转折点）
        segments = self._detect_segments(series)
        for seg in segments[1:]:  # 跳过第一个（已在整体趋势中）
            patterns.append(seg)
        
        return patterns
    
    def _generate_description(self, trend_type, strength, change_pct, series) -> str:
        """生成趋势描述"""
        strength_desc = {
            "strong": "显著",
            "moderate": "明显",
            "weak": "轻微"
        }
        
        if trend_type == "up":
            return f"呈现{strength_desc[strength]}上升趋势，总体增长{change_pct:.1%}"
        elif trend_type == "down":
            return f"呈现{strength_desc[strength]}下降趋势，总体下滑{abs(change_pct):.1%}"
        else:
            return "基本保持平稳，波动较小"
    
    def _detect_segments(self, series: pd.Series) -> List[TrendPattern]:
        """检测趋势转折点（简化实现：滑动窗口）"""
        window_size = max(len(series) // 4, 3)
        patterns = []
        
        for i in range(0, len(series) - window_size, window_size // 2):
            window = series.iloc[i:i + window_size]
            x = np.arange(len(window))
            slope, _, r_value, _, _ = stats.linregress(x, window)
            
            if abs(r_value) > 0.6:  # 强相关才认为是趋势
                change = (window.iloc[-1] - window.iloc[0]) / window.iloc[0]
                # ... 构造趋势模式
        
        return patterns
```

### 3.2 异常检测

```python
# pattern_detection/outlier.py
import numpy as np
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class OutlierPattern:
    """异常模式"""
    index: int  # 异常位置
    value: float  # 异常值
    expected_range: tuple  # 正常范围 (min, max)
    deviation: float  # 偏离程度（标准差倍数）
    description: str

class OutlierDetector:
    """异常检测器 - 使用IQR和Z-score方法"""
    
    def __init__(self, method: str = "iqr", threshold: float = 1.5):
        self.method = method  # "iqr" 或 "zscore"
        self.threshold = threshold
    
    def detect(self, series) -> List[OutlierPattern]:
        """检测异常值"""
        if self.method == "iqr":
            return self._detect_iqr(series)
        else:
            return self._detect_zscore(series)
    
    def _detect_iqr(self, series) -> List[OutlierPattern]:
        """使用IQR方法检测异常"""
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - self.threshold * IQR
        upper_bound = Q3 + self.threshold * IQR
        
        patterns = []
        for idx, val in series.items():
            if val < lower_bound or val > upper_bound:
                deviation = abs(val - series.median()) / series.std()
                
                # 生成描述
                if val > upper_bound:
                    desc = f"数值{val:.2f}明显高于正常范围，可能是异常高点"
                else:
                    desc = f"数值{val:.2f}明显低于正常范围，可能是异常低点"
                
                patterns.append(OutlierPattern(
                    index=idx,
                    value=val,
                    expected_range=(lower_bound, upper_bound),
                    deviation=deviation,
                    description=desc
                ))
        
        return patterns
    
    def _detect_zscore(self, series) -> List[OutlierPattern]:
        """使用Z-score方法检测异常"""
        z_scores = np.abs(stats.zscore(series))
        
        patterns = []
        for idx, (val, z) in enumerate(zip(series, z_scores)):
            if z > self.threshold:
                patterns.append(OutlierPattern(
                    index=idx,
                    value=val,
                    expected_range=(series.mean() - 2*series.std(), 
                                   series.mean() + 2*series.std()),
                    deviation=z,
                    description=f"Z-score为{z:.2f}，偏离均值{z:.1f}个标准差"
                ))
        
        return patterns
```

### 3.3 对比分析

```python
# pattern_detection/comparison.py
import pandas as pd
from typing import List, Dict
from scipy import stats

class ComparisonDetector:
    """对比分析检测器"""
    
    def compare_groups(self, df: pd.DataFrame, 
                       value_col: str, 
                       group_col: str) -> List[Dict]:
        """
        对比不同组之间的差异
        
        Args:
            df: 数据框
            value_col: 数值列
            group_col: 分组列
        
        Returns:
            对比发现列表
        """
        patterns = []
        
        # 按组聚合
        group_stats = df.groupby(group_col)[value_col].agg([
            'mean', 'median', 'std', 'count'
        ]).reset_index()
        
        # 找出最高和最低的组
        max_idx = group_stats['mean'].idxmax()
        min_idx = group_stats['mean'].idxmin()
        
        max_group = group_stats.iloc[max_idx]
        min_group = group_stats.iloc[min_idx]
        
        # 计算差异
        diff_pct = (max_group['mean'] - min_group['mean']) / min_group['mean']
        
        if diff_pct > 0.2:  # 差异超过20%才报告
            patterns.append({
                "type": "group_comparison",
                "finding": "group_difference",
                "description": f"{max_group[group_col]}表现最好，平均值为{max_group['mean']:.2f}，"
                              f"比{min_group[group_col]}高出{diff_pct:.1%}",
                "max_group": max_group[group_col],
                "min_group": min_group[group_col],
                "difference_percent": diff_pct,
                "recommendation": f"建议分析{max_group[group_col]}的成功经验，"
                                 f"帮助提升{min_group[group_col]}的表现"
            })
        
        # 统计显著性检验（t-test）
        groups = df[group_col].unique()
        if len(groups) == 2:
            group_a = df[df[group_col] == groups[0]][value_col]
            group_b = df[df[group_col] == groups[1]][value_col]
            
            t_stat, p_value = stats.ttest_ind(group_a, group_b)
            
            if p_value < 0.05:
                patterns.append({
                    "type": "statistical_significance",
                    "finding": "significant_difference",
                    "description": f"两组之间的差异具有统计显著性（p={p_value:.4f}）",
                    "p_value": p_value,
                    "confidence": "95%"
                })
        
        return patterns
```

---

## 四、洞察生成层

### 4.1 NLG模板系统

```python
# insight_generation/templates.py
from typing import Dict, Callable

class NLGTemplate:
    """自然语言生成模板"""
    
    # 趋势模板
    TREND_TEMPLATES = {
        "up": {
            "strong": [
                "{metric}呈现强劲增长态势，整体上升{change_percent:.1%}",
                "{metric}表现亮眼，实现了{change_percent:.1%}的显著增长",
                "{metric}持续走高，增幅达到{change_percent:.1%}"
            ],
            "moderate": [
                "{metric}稳步上升，总体增长{change_percent:.1%}",
                "{metric}保持增长势头，增幅为{change_percent:.1%}"
            ],
            "weak": [
                "{metric}略有上升，增长{change_percent:.1%}",
                "{metric}呈现微弱增长态势"
            ]
        },
        "down": {
            "strong": [
                "⚠️ {metric}大幅下滑{change_percent:.1%}，需要引起高度重视",
                "{metric}出现明显下滑，跌幅达{change_percent:.1%}",
                "警告：{metric}显著下降{change_percent:.1%}"
            ],
            "moderate": [
                "{metric}呈下降趋势，总体下滑{change_percent:.1%}",
                "{metric}有所回落，降幅为{change_percent:.1%}"
            ],
            "weak": [
                "{metric}轻微下滑{change_percent:.1%}",
                "{metric}呈现小幅下降"
            ]
        },
        "flat": [
            "{metric}整体保持平稳",
            "{metric}波动较小，处于稳定状态"
        ]
    }
    
    # 异常模板
    OUTLIER_TEMPLATES = [
        "注意到{metric}在{time}出现异常，数值为{value:.2f}，{description}",
        "发现异常点：{metric}在{time}达到{value:.2f}，{description}",
        "⚠️ 异常提醒：{metric}在{time}出现异常值{value:.2f}"
    ]
    
    # 对比模板
    COMPARISON_TEMPLATES = [
        "{group_a}表现优于{group_b}，差距为{difference:.1%}",
        "对比发现：{group_a}的{metric}比{group_b}高出{difference:.1%}",
        "{group_a}领先，{metric}比{group_b}多{difference:.1%}"
    ]
    
    @classmethod
    def render_trend(cls, pattern) -> str:
        """渲染趋势描述"""
        import random
        
        if pattern.type == "flat":
            return random.choice(cls.TREND_TEMPLATES["flat"]).format(
                metric=pattern.metric_name
            )
        
        templates = cls.TREND_TEMPLATES[pattern.type][pattern.strength]
        return random.choice(templates).format(
            metric=pattern.metric_name,
            change_percent=abs(pattern.change_percent)
        )
    
    @classmethod
    def render_outlier(cls, pattern, metric_name: str) -> str:
        """渲染异常描述"""
        import random
        return random.choice(cls.OUTLIER_TEMPLATES).format(
            metric=metric_name,
            time=pattern.index,
            value=pattern.value,
            description=pattern.description
        )
```

### 4.2 洞察生成器

```python
# insight_generation/generator.py
from typing import List, Dict
from dataclasses import dataclass
import pandas as pd

@dataclass
class Insight:
    """洞察"""
    id: str
    type: str  # "trend", "outlier", "comparison", "distribution"
    priority: int  # 1-10，越高越重要
    title: str  # 简短标题
    description: str  # 详细描述
    data_evidence: Dict  # 支撑数据
    recommendation: str  # 建议行动
    visualization_type: str  # 建议图表类型

class InsightGenerator:
    """洞察生成器"""
    
    def __init__(self):
        self.trend_detector = TrendDetector()
        self.outlier_detector = OutlierDetector()
        self.comparison_detector = ComparisonDetector()
        self.template = NLGTemplate()
    
    def generate(self, df: pd.DataFrame, 
                 metric_columns: List[str],
                 dimensions: List[str] = None,
                 time_column: str = None) -> List[Insight]:
        """
        生成数据洞察
        
        Args:
            df: 数据框
            metric_columns: 指标列名列表
            dimensions: 维度列名列表
            time_column: 时间列名
        
        Returns:
            洞察列表
        """
        insights = []
        
        for metric in metric_columns:
            series = df[metric]
            
            # 1. 趋势洞察
            if time_column and time_column in df.columns:
                trend_patterns = self.trend_detector.detect(series, df[time_column])
                for pattern in trend_patterns:
                    insights.append(self._create_trend_insight(metric, pattern))
            
            # 2. 异常洞察
            outlier_patterns = self.outlier_detector.detect(series)
            for pattern in outlier_patterns:
                insights.append(self._create_outlier_insight(metric, pattern))
            
            # 3. 对比洞察
            if dimensions:
                for dim in dimensions:
                    if dim in df.columns:
                        comp_patterns = self.comparison_detector.compare_groups(
                            df, metric, dim
                        )
                        for pattern in comp_patterns:
                            insights.append(
                                self._create_comparison_insight(metric, dim, pattern)
                            )
        
        # 按优先级排序
        insights.sort(key=lambda x: x.priority, reverse=True)
        
        return insights
    
    def _create_trend_insight(self, metric: str, pattern) -> Insight:
        """创建趋势洞察"""
        # 优先级：强趋势 > 中等趋势 > 弱趋势
        priority_map = {"strong": 9, "moderate": 6, "weak": 3}
        priority = priority_map.get(pattern.strength, 3)
        
        # 下降趋势优先级更高（可能是问题）
        if pattern.type == "down":
            priority += 2
        
        description = self.template.render_trend(pattern)
        
        # 生成建议
        if pattern.type == "down" and pattern.strength == "strong":
            recommendation = f"建议深入分析{metric}下滑原因，制定改进措施"
        elif pattern.type == "up" and pattern.strength == "strong":
            recommendation = f"建议总结{metric}增长经验，推广成功做法"
        else:
            recommendation = f"持续监控{metric}变化趋势"
        
        return Insight(
            id=f"trend_{metric}_{hash(description) % 10000}",
            type="trend",
            priority=priority,
            title=f"{metric}趋势分析",
            description=description,
            data_evidence={
                "change_percent": pattern.change_percent,
                "confidence": pattern.confidence,
                "start_value": pattern.start_value,
                "end_value": pattern.end_value
            },
            recommendation=recommendation,
            visualization_type="line"  # 趋势用折线图
        )
    
    def _create_outlier_insight(self, metric: str, pattern) -> Insight:
        """创建异常洞察"""
        description = self.template.render_outlier(pattern, metric)
        
        # 异常优先级与偏离程度相关
        priority = min(int(pattern.deviation * 2), 10)
        
        return Insight(
            id=f"outlier_{metric}_{pattern.index}",
            type="outlier",
            priority=priority,
            title=f"{metric}异常检测",
            description=description,
            data_evidence={
                "index": pattern.index,
                "value": pattern.value,
                "expected_range": pattern.expected_range,
                "deviation": pattern.deviation
            },
            recommendation=f"建议检查该时间点的业务情况，确认是否为真实异常",
            visualization_type="scatter"  # 异常用散点图
        )
    
    def _create_comparison_insight(self, metric: str, dimension: str, 
                                   pattern: Dict) -> Insight:
        """创建对比洞察"""
        return Insight(
            id=f"comparison_{metric}_{dimension}",
            type="comparison",
            priority=5,
            title=f"{dimension}维度{metric}对比",
            description=pattern["description"],
            data_evidence=pattern,
            recommendation=pattern.get("recommendation", ""),
            visualization_type="bar"  # 对比用柱状图
        )
```

---

## 五、叙事构建层

### 5.1 叙事结构

```python
# narrative_building/structure.py
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class NarrativeSection:
    """叙事章节"""
    title: str
    type: str  # "intro", "key_findings", "details", "recommendations"
    content: str
    insights: List[str]  # 关联的洞察ID

class NarrativeBuilder:
    """叙事构建器"""
    
    def __init__(self, max_insights: int = 5):
        self.max_insights = max_insights
    
    def build(self, insights: List, kpi_stats: Dict) -> List[NarrativeSection]:
        """
        构建完整叙事
        
        Returns:
            叙事章节列表
        """
        sections = []
        
        # 1. 开头：总体概况
        sections.append(self._build_intro(kpi_stats))
        
        # 2. 主体：关键发现（取优先级最高的N个）
        top_insights = insights[:self.max_insights]
        sections.append(self._build_key_findings(top_insights))
        
        # 3. 详细分析
        if len(insights) > self.max_insights:
            other_insights = insights[self.max_insights:]
            sections.append(self._build_details(other_insights))
        
        # 4. 结尾：行动建议
        sections.append(self._build_recommendations(top_insights))
        
        return sections
    
    def _build_intro(self, kpi_stats: Dict) -> NarrativeSection:
        """构建开头章节"""
        content = f"""## 总体概况

本报告分析了 **{kpi_stats.get('total_records', 'N')}** 条数据，涵盖了关键业务指标的表现。

**核心指标**：
- 平均值：{kpi_stats.get('mean', 'N/A'):.2f}
- 中位数：{kpi_stats.get('median', 'N/A'):.2f}
- 最大值：{kpi_stats.get('max', 'N/A'):.2f}
- 最小值：{kpi_stats.get('min', 'N/A'):.2f}

以下是详细的数据洞察和分析建议。
"""
        return NarrativeSection(
            title="总体概况",
            type="intro",
            content=content,
            insights=[]
        )
    
    def _build_key_findings(self, insights: List) -> NarrativeSection:
        """构建关键发现章节"""
        content = "## 关键发现\n\n"
        
        for i, insight in enumerate(insights, 1):
            priority_mark = "" if insight.priority >= 8 else "🟡" if insight.priority >= 5 else "🟢"
            content += f"""### {i}. {priority_mark} {insight.title}

{insight.description}

**数据支撑**：{self._format_evidence(insight.data_evidence)}

**建议行动**：{insight.recommendation}

**推荐可视化**：{self._get_viz_name(insight.visualization_type)}

---

"""
        
        return NarrativeSection(
            title="关键发现",
            type="key_findings",
            content=content,
            insights=[ins.id for ins in insights]
        )
    
    def _build_recommendations(self, insights: List) -> NarrativeSection:
        """构建行动建议章节"""
        # 汇总所有建议
        all_recommendations = [ins.recommendation for ins in insights if ins.recommendation]
        
        content = "## 行动建议\n\n基于以上分析，我们建议您采取以下行动：\n\n"
        
        for i, rec in enumerate(all_recommendations[:5], 1):
            content += f"{i}. {rec}\n"
        
        content += "\n建议持续关注这些指标的变化，及时调整策略。"
        
        return NarrativeSection(
            title="行动建议",
            type="recommendations",
            content=content,
            insights=[ins.id for ins in insights]
        )
    
    def _format_evidence(self, evidence: Dict) -> str:
        """格式化数据证据"""
        parts = []
        for key, value in evidence.items():
            if isinstance(value, float):
                parts.append(f"{key}={value:.2f}")
            else:
                parts.append(f"{key}={value}")
        return ", ".join(parts)
    
    def _get_viz_name(self, viz_type: str) -> str:
        """获取可视化类型名称"""
        names = {
            "line": "折线图",
            "bar": "柱状图",
            "scatter": "散点图",
            "pie": "饼图",
            "heatmap": "热力图"
        }
        return names.get(viz_type, viz_type)
```

---

## 六、API 设计

```python
# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd

app = FastAPI(title="RATH Narrative Service")

class AnalyzeRequest(BaseModel):
    data: List[Dict[str, Any]]  # 数据
    metric_columns: List[str]   # 指标列
    dimension_columns: Optional[List[str]] = None  # 维度列
    time_column: Optional[str] = None  # 时间列
    max_insights: int = 5  # 最大洞察数量
    language: str = "zh"  # 语言

class AnalyzeResponse(BaseModel):
    success: bool
    narrative: str  # 完整叙事文本
    sections: List[Dict]  # 章节结构
    insights: List[Dict]  # 洞察列表
    visualizations: List[Dict]  # 可视化建议
    message: str

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_data(request: AnalyzeRequest):
    """分析数据并生成洞察报告"""
    try:
        # 转换为DataFrame
        df = pd.DataFrame(request.data)
        
        # 生成洞察
        generator = InsightGenerator()
        insights = generator.generate(
            df,
            request.metric_columns,
            request.dimension_columns,
            request.time_column
        )
        
        # 计算KPI统计
        kpi_stats = df[request.metric_columns[0]].describe().to_dict()
        
        # 构建叙事
        builder = NarrativeBuilder(max_insights=request.max_insights)
        sections = builder.build(insights, kpi_stats)
        
        # 组装完整叙事
        narrative = "\n\n".join([section.content for section in sections])
        
        # 提取可视化建议
        visualizations = [
            {
                "insight_id": ins.id,
                "type": ins.visualization_type,
                "title": ins.title
            }
            for ins in insights[:request.max_insights]
        ]
        
        return AnalyzeResponse(
            success=True,
            narrative=narrative,
            sections=[
                {
                    "title": s.title,
                    "type": s.type,
                    "insights": s.insights
                }
                for s in sections
            ],
            insights=[
                {
                    "id": ins.id,
                    "type": ins.type,
                    "priority": ins.priority,
                    "title": ins.title,
                    "description": ins.description
                }
                for ins in insights[:request.max_insights]
            ],
            visualizations=visualizations,
            message="分析报告生成成功"
        )
        
    except Exception as e:
        return AnalyzeResponse(
            success=False,
            narrative="",
            sections=[],
            insights=[],
            visualizations=[],
            message=str(e)
        )
```

---

## 七、总结

narrative-service 是 RATH 的"数据讲故事"引擎：

| 亮点 | 说明 |
|------|------|
| **全自动** | 无需人工编写，自动生成报告 |
| **多维度** | 趋势、异常、对比全覆盖 |
| **可解释** | 每个洞察都有数据支撑和建议 |
| **可视化引导** | 自动推荐合适的图表类型 |

**适用场景**:
- 自动化周报/月报生成
- 数据监控告警解释
- 探索性数据分析辅助
- 向非技术人员解释数据发现

**借鉴价值**: ⭐⭐⭐⭐
- 学习规则+模板结合的NLG方法
- 洞察优先级排序逻辑
- 叙事结构组织方式
