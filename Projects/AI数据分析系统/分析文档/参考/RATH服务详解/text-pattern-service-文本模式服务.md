# RATH text-pattern-service：文本模式识别服务详解

**服务定位**: 自动化文本数据模式识别与分析  
**技术栈**: Python + FastAPI + NLP + 正则表达式引擎  
**默认端口**: 5005  
**所属项目**: [RATH](https://github.com/Kanaries/RATH)

---

## 一、服务概述

### 1.1 什么是 text-pattern-service？

text-pattern-service 是 RATH 处理**非结构化/半结构化文本数据**的专用服务：

```
┌─────────────────────────────────────────────────────────────┐
│                text-pattern-service :5005                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  原始文本数据                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  用户反馈、日志、产品描述、地址、邮箱...              │   │
│  │                                                     │   │
│  │  "2024-01-15 ERROR: Connection timeout at           │   │
│  │   192.168.1.1:8080"                                 │   │
│  │                                                     │   │
│  │  "客户邮箱：zhangsan@gmail.com，电话：138****5678"  │   │
│  │                                                     │   │
│  │  "地址：北京市海淀区中关村大街1号100080"             │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  text-pattern-service                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. 模式识别：发现文本中的结构化模式                  │   │
│  │    - 日期时间格式                                   │   │
│  │    - 邮箱/电话/URL                                  │   │
│  │    - 日志级别/错误码                                │   │
│  │    - 地址/邮编                                      │   │
│  │                                                     │   │
│  │ 2. 提取结构化信息                                   │   │
│  │    日期 → 年、月、日、星期                          │   │
│  │    地址 → 省、市、区、街道                          │   │
│  │                                                     │   │
│  │ 3. 数据清洗与标准化                                 │   │
│  │    多种日期格式 → 统一格式                          │   │
│  │    各种电话格式 → 标准格式                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  结构化数据                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 日期时间: 2024-01-15 10:30:00                       │   │
│  │ ├─ year: 2024                                      │   │
│  │ ├─ month: 1                                        │   │
│  │ ├─ day: 15                                         │   │
│  │ └─ weekday: Monday                                 │   │
│  │                                                     │   │
│  │ 错误信息: ERROR: Connection timeout                 │   │
│  │ ├─ level: ERROR                                    │   │
│  │ ├─ message: Connection timeout                     │   │
│  │ └─ ip: 192.168.1.1                                 │   │
│  │                                                     │   │
│  │ 联系方式: zhangsan@gmail.com                        │   │
│  │ ├─ type: email                                     │   │
│  │ ├─ user: zhangsan                                  │   │
│  │ └─ domain: gmail.com                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心能力

| 能力 | 说明 | 技术 |
|------|------|------|
| **模式发现** | 自动识别文本中的结构化模式 | 正则表达式、统计模式 |
| **信息提取** | 从文本提取结构化字段 | NER、正则、规则引擎 |
| **数据标准化** | 统一不同格式的数据 | 转换规则库 |
| **异常检测** | 发现不符合已知模式的文本 | 异常检测算法 |
| **文本分类** | 自动分类日志/反馈类型 | 机器学习分类 |

---

## 二、技术架构

### 2.1 项目结构

```
text-pattern-service/
├── main.py                 # FastAPI 入口
├── models.py              # Pydantic 模型
├── requirements.txt       # 依赖
├── Dockerfile            # 容器定义
├── pattern_engine/       # 模式引擎
│   ├── __init__.py
│   ├── detector.py       # 模式检测器
│   ├── regex_lib.py      # 正则库
│   └── stats_analyzer.py # 统计分析器
├── extractors/           # 提取器
│   ├── __init__.py
│   ├── date_extractor.py # 日期提取
│   ├── email_extractor.py# 邮箱提取
│   ├── phone_extractor.py# 电话提取
│   ├── log_extractor.py  # 日志提取
│   └── address_extractor.py # 地址提取
├── standardizers/        # 标准化器
│   ├── __init__.py
│   ├── date_std.py       # 日期标准化
│   └── phone_std.py      # 电话标准化
└── nlp/                  # NLP模块
    ├── __init__.py
    └── classifier.py     # 文本分类
```

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                text-pattern-service :5005                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FastAPI Layer                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ POST /detect             # 检测文本模式             │   │
│  │ POST /extract            # 提取结构化信息           │   │
│  │ POST /standardize        # 标准化数据               │   │
│  │ POST /analyze_column     # 分析整列数据             │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  Pattern Engine                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. 统计分析（字符分布、长度分布）                     │   │
│  │ 2. 模式匹配（正则库）                                │   │
│  │ 3. 模式排序（按匹配度）                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  Extractors                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  Date    │ │  Email   │ │  Phone   │ │   Log    │      │
│  │ Extractor│ │ Extractor│ │ Extractor│ │ Extractor│      │
│  │          │ │          │ │          │ │          │      │
│  │ 日期解析 │ │ 邮箱解析 │ │ 电话解析 │ │ 日志解析 │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                           ↓                                  │
│  Standardizers                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 统一格式输出（ISO日期、标准电话等）                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、模式引擎设计

### 3.1 正则表达式库

```python
# pattern_engine/regex_lib.py
import re
from typing import Dict, Pattern

class RegexLibrary:
    """
    常用文本模式正则库
    可扩展、可自定义
    """
    
    # 日期时间模式
    DATE_PATTERNS = {
        "iso_date": {
            "pattern": r"(\d{4})-(\d{2})-(\d{2})",
            "example": "2024-01-15",
            "groups": ["year", "month", "day"]
        },
        "chinese_date": {
            "pattern": r"(\d{4})年(\d{1,2})月(\d{1,2})日",
            "example": "2024年1月15日",
            "groups": ["year", "month", "day"]
        },
        "slash_date": {
            "pattern": r"(\d{1,2})/(\d{1,2})/(\d{4})",
            "example": "01/15/2024",
            "groups": ["month", "day", "year"]
        },
        "datetime_iso": {
            "pattern": r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})",
            "example": "2024-01-15T10:30:00",
            "groups": ["date", "time"]
        }
    }
    
    # 邮箱模式
    EMAIL_PATTERN = {
        "email": {
            "pattern": r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            "example": "user@example.com",
            "groups": ["user", "domain"]
        }
    }
    
    # 电话模式
    PHONE_PATTERNS = {
        "china_mobile": {
            "pattern": r"1[3-9]\d{9}",
            "example": "13800138000",
            "groups": ["full_number"]
        },
        "china_mobile_formatted": {
            "pattern": r"1[3-9]\d-?\d{4}-?\d{4}",
            "example": "138-0013-8000",
            "groups": ["full_number"]
        },
        "international": {
            "pattern": r"\+(\d{1,3})[ -]?(\d{1,4})[ -]?(\d{1,4})[ -]?(\d{1,4})",
            "example": "+86 138 0013 8000",
            "groups": ["country", "area", "prefix", "line"]
        }
    }
    
    # 日志模式
    LOG_PATTERNS = {
        "standard_log": {
            "pattern": r"(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.+)",
            "example": "2024-01-15 10:30:00 ERROR Connection timeout",
            "groups": ["timestamp", "level", "message"]
        },
        "syslog": {
            "pattern": r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.+)",
            "example": "Jan 15 10:30:00 server ERROR: Disk full",
            "groups": ["timestamp", "host", "message"]
        }
    }
    
    # IP地址模式
    IP_PATTERN = {
        "ipv4": {
            "pattern": r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)",
            "example": "192.168.1.1",
            "groups": ["ip"]
        }
    }
    
    # URL模式
    URL_PATTERN = {
        "url": {
            "pattern": r"https?://([^/\s]+)(/[^\s]*)?",
            "example": "https://example.com/path",
            "groups": ["domain", "path"]
        }
    }
    
    @classmethod
    def get_all_patterns(cls) -> Dict[str, Dict]:
        """获取所有预定义模式"""
        all_patterns = {}
        all_patterns.update(cls.DATE_PATTERNS)
        all_patterns.update(cls.EMAIL_PATTERN)
        all_patterns.update(cls.PHONE_PATTERNS)
        all_patterns.update(cls.LOG_PATTERNS)
        all_patterns.update(cls.IP_PATTERN)
        all_patterns.update(cls.URL_PATTERN)
        return all_patterns
    
    @classmethod
    def compile_patterns(cls) -> Dict[str, Pattern]:
        """编译所有正则表达式"""
        compiled = {}
        for name, config in cls.get_all_patterns().items():
            compiled[name] = re.compile(config["pattern"])
        return compiled
```

### 3.2 模式检测器

```python
# pattern_engine/detector.py
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import Counter

@dataclass
class DetectedPattern:
    """检测到的模式"""
    pattern_name: str
    pattern_type: str  # "date", "email", "phone", "log", etc.
    confidence: float  # 0-1
    matched_count: int
    example: str
    coverage: float  # 覆盖率

class PatternDetector:
    """模式检测器"""
    
    def __init__(self):
        self.compiled_patterns = RegexLibrary.compile_patterns()
        self.pattern_types = self._build_type_mapping()
    
    def _build_type_mapping(self) -> Dict[str, str]:
        """构建模式名到类型的映射"""
        mapping = {}
        for name in RegexLibrary.DATE_PATTERNS:
            mapping[name] = "date"
        for name in RegexLibrary.EMAIL_PATTERN:
            mapping[name] = "email"
        for name in RegexLibrary.PHONE_PATTERNS:
            mapping[name] = "phone"
        for name in RegexLibrary.LOG_PATTERNS:
            mapping[name] = "log"
        for name in RegexLibrary.IP_PATTERN:
            mapping[name] = "ip"
        for name in RegexLibrary.URL_PATTERN:
            mapping[name] = "url"
        return mapping
    
    def detect_column_patterns(self, values: List[str]) -> List[DetectedPattern]:
        """
        检测数据列中的主要模式
        
        Args:
            values: 列中的所有值
        
        Returns:
            检测到的模式列表，按置信度排序
        """
        total = len(values)
        pattern_scores = {}
        
        for pattern_name, pattern in self.compiled_patterns.items():
            matches = 0
            example = None
            
            for value in values:
                if pattern.search(str(value)):
                    matches += 1
                    if example is None:
                        example = value
            
            if matches > 0:
                coverage = matches / total
                # 置信度 = 覆盖率 * (1 - 多样性惩罚)
                # 如果匹配的模式类型太多，可能说明匹配太宽泛
                confidence = coverage
                
                pattern_scores[pattern_name] = DetectedPattern(
                    pattern_name=pattern_name,
                    pattern_type=self.pattern_types.get(pattern_name, "unknown"),
                    confidence=confidence,
                    matched_count=matches,
                    example=example,
                    coverage=coverage
                )
        
        # 按置信度排序
        sorted_patterns = sorted(
            pattern_scores.values(),
            key=lambda x: x.confidence,
            reverse=True
        )
        
        return sorted_patterns
    
    def detect_row_patterns(self, text: str) -> List[Dict]:
        """
        检测单行文本中的所有模式
        
        Returns:
            该行中匹配的所有模式及位置
        """
        matches = []
        
        for pattern_name, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(text):
                groups = match.groups()
                pattern_config = RegexLibrary.get_all_patterns()[pattern_name]
                
                matches.append({
                    "pattern": pattern_name,
                    "type": self.pattern_types.get(pattern_name, "unknown"),
                    "start": match.start(),
                    "end": match.end(),
                    "matched_text": match.group(0),
                    "groups": {
                        name: value 
                        for name, value in zip(pattern_config["groups"], groups)
                    } if groups else {}
                })
        
        # 按位置排序
        matches.sort(key=lambda x: x["start"])
        return matches
```

---

## 四、提取器设计

### 4.1 日期提取器

```python
# extractors/date_extractor.py
from datetime import datetime
from typing import Dict, Optional, Tuple
import re

class DateExtractor:
    """日期提取器 - 支持多种格式"""
    
    def extract(self, text: str) -> Optional[Dict]:
        """从文本提取日期"""
        # 尝试各种日期格式
        extractors = [
            self._extract_iso,
            self._extract_chinese,
            self._extract_slash
        ]
        
        for extractor in extractors:
            result = extractor(text)
            if result:
                return result
        
        return None
    
    def _extract_iso(self, text: str) -> Optional[Dict]:
        """提取ISO格式日期 2024-01-15"""
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
        if match:
            year, month, day = match.groups()
            return {
                "original": match.group(0),
                "format": "iso",
                "year": int(year),
                "month": int(month),
                "day": int(day),
                "datetime": datetime(int(year), int(month), int(day))
            }
        return None
    
    def _extract_chinese(self, text: str) -> Optional[Dict]:
        """提取中文格式日期 2024年1月15日"""
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
        if match:
            year, month, day = match.groups()
            return {
                "original": match.group(0),
                "format": "chinese",
                "year": int(year),
                "month": int(month),
                "day": int(day),
                "datetime": datetime(int(year), int(month), int(day))
            }
        return None
    
    def _extract_slash(self, text: str) -> Optional[Dict]:
        """提取斜杠格式日期 01/15/2024"""
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
        if match:
            month, day, year = match.groups()
            return {
                "original": match.group(0),
                "format": "us",
                "year": int(year),
                "month": int(month),
                "day": int(day),
                "datetime": datetime(int(year), int(month), int(day))
            }
        return None
    
    def standardize(self, extracted: Dict, target_format: str = "iso") -> str:
        """
        标准化日期格式
        
        Args:
            extracted: 提取的日期信息
            target_format: 目标格式 ("iso", "chinese", "us")
        
        Returns:
            标准化后的日期字符串
        """
        dt = extracted.get("datetime")
        if not dt:
            return extracted.get("original", "")
        
        if target_format == "iso":
            return dt.strftime("%Y-%m-%d")
        elif target_format == "chinese":
            return dt.strftime("%Y年%m月%d日")
        elif target_format == "us":
            return dt.strftime("%m/%d/%Y")
        else:
            return dt.strftime("%Y-%m-%d")
```

### 4.2 日志提取器

```python
# extractors/log_extractor.py
import re
from typing import Dict, List
from datetime import datetime

class LogExtractor:
    """日志提取器 - 解析各类日志格式"""
    
    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "WARN", "ERROR", "FATAL", "CRITICAL"]
    
    def extract(self, log_line: str) -> Dict:
        """提取日志信息"""
        result = {
            "original": log_line,
            "timestamp": None,
            "level": None,
            "message": log_line,
            "metadata": {}
        }
        
        # 提取时间戳
        timestamp = self._extract_timestamp(log_line)
        if timestamp:
            result["timestamp"] = timestamp
        
        # 提取日志级别
        level = self._extract_level(log_line)
        if level:
            result["level"] = level
        
        # 提取IP地址
        ip = self._extract_ip(log_line)
        if ip:
            result["metadata"]["ip"] = ip
        
        # 提取错误码
        error_code = self._extract_error_code(log_line)
        if error_code:
            result["metadata"]["error_code"] = error_code
        
        # 清理消息（移除时间戳、级别等已知信息）
        result["message"] = self._clean_message(log_line, result)
        
        return result
    
    def _extract_timestamp(self, log: str) -> Optional[datetime]:
        """提取时间戳"""
        # ISO格式
        match = re.search(r'(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})', log)
        if match:
            try:
                return datetime.fromisoformat(match.group(1).replace(' ', 'T'))
            except:
                pass
        return None
    
    def _extract_level(self, log: str) -> Optional[str]:
        """提取日志级别"""
        for level in self.LOG_LEVELS:
            if re.search(rf'\b{level}\b', log, re.IGNORECASE):
                return level.upper()
        return None
    
    def _extract_ip(self, log: str) -> Optional[str]:
        """提取IP地址"""
        ip_pattern = r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
        match = re.search(ip_pattern, log)
        return match.group(0) if match else None
    
    def _extract_error_code(self, log: str) -> Optional[str]:
        """提取错误码（如 ERR001、E1234等）"""
        patterns = [
            r'ERR[\-\s]?(\d+)',
            r'E(\d{3,4})',
            r'ERROR[\s:]*(\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, log, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def _clean_message(self, log: str, extracted: Dict) -> str:
        """清理日志消息"""
        message = log
        
        # 移除时间戳
        if extracted.get("timestamp"):
            message = re.sub(r'\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}', '', message)
        
        # 移除日志级别
        if extracted.get("level"):
            message = re.sub(rf'\b{extracted["level"]}\b', '', message, flags=re.IGNORECASE)
        
        # 移除多余空格
        message = re.sub(r'\s+', ' ', message).strip()
        
        return message
```

---

## 五、API 设计

```python
# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

app = FastAPI(title="RATH Text Pattern Service")

class DetectRequest(BaseModel):
    values: List[str]  # 待检测的文本列表
    min_coverage: float = 0.5  # 最小覆盖率

class DetectResponse(BaseModel):
    success: bool
    patterns: List[Dict]  # 检测到的模式
    recommended_extractor: str  # 推荐的提取器
    message: str

@app.post("/detect", response_model=DetectResponse)
async def detect_patterns(request: DetectRequest):
    """检测文本数据中的模式"""
    try:
        detector = PatternDetector()
        patterns = detector.detect_column_patterns(request.values)
        
        # 过滤低覆盖率的模式
        filtered = [p for p in patterns if p.coverage >= request.min_coverage]
        
        # 推荐提取器（取最高置信度的类型）
        recommended = filtered[0].pattern_type if filtered else "unknown"
        
        return DetectResponse(
            success=True,
            patterns=[
                {
                    "name": p.pattern_name,
                    "type": p.pattern_type,
                    "confidence": p.confidence,
                    "coverage": p.coverage,
                    "matched_count": p.matched_count,
                    "example": p.example
                }
                for p in filtered[:5]  # 返回前5个
            ],
            recommended_extractor=recommended,
            message=f"检测到{len(filtered)}种主要模式"
        )
        
    except Exception as e:
        return DetectResponse(
            success=False,
            patterns=[],
            recommended_extractor="unknown",
            message=str(e)
        )


class ExtractRequest(BaseModel):
    values: List[str]
    extractor_type: str  # "date", "email", "phone", "log", "auto"

class ExtractResponse(BaseModel):
    success: bool
    extracted: List[Dict]  # 提取的结构化数据
    failed_count: int  # 提取失败的数量
    message: str

@app.post("/extract", response_model=ExtractResponse)
async def extract_info(request: ExtractRequest):
    """从文本中提取结构化信息"""
    try:
        extractor = get_extractor(request.extractor_type)
        
        results = []
        failed = 0
        
        for value in request.values:
            try:
                result = extractor.extract(value)
                if result:
                    results.append(result)
                else:
                    failed += 1
            except:
                failed += 1
        
        return ExtractResponse(
            success=True,
            extracted=results,
            failed_count=failed,
            message=f"成功提取{len(results)}条，失败{failed}条"
        )
        
    except Exception as e:
        return ExtractResponse(
            success=False,
            extracted=[],
            failed_count=len(request.values),
            message=str(e)
        )


def get_extractor(extractor_type: str):
    """获取提取器实例"""
    extractors = {
        "date": DateExtractor(),
        "email": EmailExtractor(),
        "phone": PhoneExtractor(),
        "log": LogExtractor(),
        "auto": AutoExtractor()  # 自动选择
    }
    return extractors.get(extractor_type, extractors["auto"])
```

---

## 六、使用示例

### 6.1 检测文本模式

```python
import requests

# 检测一列日志数据的模式
logs = [
    "2024-01-15 10:30:00 ERROR Connection timeout",
    "2024-01-15 10:31:15 INFO User login successful",
    "2024-01-15 10:32:00 WARN High memory usage",
    # ... 更多日志
]

response = requests.post("http://text-pattern:5005/detect", json={
    "values": logs,
    "min_coverage": 0.8
})

result = response.json()
print(result)
# {
#   "patterns": [
#     {
#       "name": "standard_log",
#       "type": "log",
#       "confidence": 0.95,
#       "coverage": 0.98,
#       "example": "2024-01-15 10:30:00 ERROR Connection timeout"
#     }
#   ],
#   "recommended_extractor": "log"
# }
```

### 6.2 提取结构化信息

```python
# 提取日志信息
response = requests.post("http://text-pattern:5005/extract", json={
    "values": logs,
    "extractor_type": "log"
})

result = response.json()
print(result["extracted"][0])
# {
#   "original": "2024-01-15 10:30:00 ERROR Connection timeout",
#   "timestamp": "2024-01-15T10:30:00",
#   "level": "ERROR",
#   "message": "Connection timeout",
#   "metadata": {}
# }
```

---

## 七、总结

text-pattern-service 是 RATH 处理文本数据的利器：

| 亮点 | 说明 |
|------|------|
| **自动识别** | 无需预先定义，自动发现文本模式 |
| **多格式支持** | 日期、邮箱、电话、日志全覆盖 |
| **可扩展** | 易于添加新的模式定义 |
| **标准化** | 统一不同格式的数据表示 |

**适用场景**:
- 日志分析
- 数据清洗前的模式识别
- 非结构化数据提取结构化字段
- 数据质量检查

**借鉴价值**: ⭐⭐⭐
- 学习正则库的组织方式
- 模式检测的统计方法
- 提取器的插件化设计
