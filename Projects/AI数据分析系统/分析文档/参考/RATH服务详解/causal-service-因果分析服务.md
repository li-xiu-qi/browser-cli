# RATH causal-service：因果分析服务详解

**服务定位**: 因果发现与因果推断核心引擎  
**技术栈**: Python + FastAPI + causal-learn + DoWhy  
**默认端口**: 5002  
**所属项目**: [RATH](https://github.com/Kanaries/RATH)

---

## 一、服务概述

### 1.1 什么是因果分析？

causal-service 是 RATH 最核心的差异化服务，提供**因果发现**和**因果推断**两大能力：

```
【因果发现】                    【因果推断】
数据 → 因果图                   因果图 + 干预 → 结果

例：销售数据                     例：因果图已发现
┌─────────┐                    营销投入 → 销售额
│ 营销费用 │──┐                  ↓
│ 季节    │──┼→ 【PC算法】 →    问：如果增加10万营销预算
│ 销售额  │──┘                  销售额会增加多少？
│ 竞品价格 │                      
└─────────┘                    答：预计增加25万（置信区间...）

        ↓                              ↓
   发现：营销 → 销售额              量化干预效果
   季节 → 营销（混杂）              支持What-if分析
```

### 1.2 核心能力

| 能力 | 说明 | 算法 |
|------|------|------|
| **因果发现** | 从观测数据中自动发现因果关系 | PC、GES、NOTEARS |
| **因果推断** | 估计干预效果和反事实结果 | DoWhy + EconML |
| **What-if分析** | 模拟干预场景 | 因果模型推理 |
| **因果图可视化** | 生成可交互的因果图 | 自定义布局算法 |

---

## 二、技术架构

### 2.1 项目结构

```
causal-service/
├── main.py                 # FastAPI 入口
├── interfaces.py           # Pydantic 接口定义
├── requirements.txt        # 依赖
├── Dockerfile             # 容器定义
├── algorithms/            # 算法实现目录
│   ├── __init__.py
│   ├── common.py          # 算法基类
│   ├── pc.py             # PC算法
│   ├── ges.py            # GES算法
│   ├── granger.py        # Granger因果
│   ├── notears.py        # NOTEARS算法
│   └── dowhy_wrapper.py  # DoWhy封装
├── causallearn/          # causal-learn库集成
│   └── ...
└── dowhy/                # DoWhy库集成
    └── ...
```

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    causal-service :5002                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FastAPI Layer                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ POST /algo/{name}/run    # 执行算法                 │   │
│  │ POST /algo/list          # 获取算法列表             │   │
│  │ GET  /health             # 健康检查                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  Algorithm Registry                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ algorithms.DICT = {                                  │   │
│  │   "PC": PCAlgorithm(),                              │   │
│  │   "GES": GESAlgorithm(),                            │   │
│  │   "Granger": GrangerAlgorithm(),                    │   │
│  │   "DoWhy": DoWhyWrapper()                           │   │
│  │ }                                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  Algorithm Implementations                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ PC算法   │ │ GES算法  │ │Granger   │ │DoWhy     │      │
│  │          │ │          │ │因果      │ │推断      │      │
│  │causal-   │ │causal-   │ │statsmodels│ │dowhy     │      │
│  │learn     │ │learn     │ │          │ │econml    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、核心算法详解

### 3.1 PC算法（Peter-Clark算法）

**原理**: 基于条件独立性检验，逐步构建因果图

**适用场景**: 
- 变量间因果关系不明
- 需要发现隐藏的混杂因素
- 数据量中等（<1000样本）

**算法流程**:
```
输入：观测数据 D，变量集 V，显著性水平 α

Step 1: 骨架学习
  对每个变量对 (Xi, Xj):
    测试条件独立性 Xi ⟂ Xj | S，其中 S ⊆ V\{Xi,Xj}
    如果独立，则无边 Xi — Xj
    否则，添加边 Xi — Xj

Step 2: 定向
  对每个结构 Xi — Xk — Xj:
    如果 Xk 不在分离集 S 中:
      定向为 Xi → Xk ← Xj (V结构)

Step 3: 传播定向
  应用定向规则直到无法继续

输出：因果图（部分边可能无向）
```

**代码实现**:
```python
# algorithms/pc.py
from causallearn.search.ConstraintBased.PC import pc
from causallearn.utils.cit import fisherz

class PCAlgorithm(AlgoInterface):
    """PC因果发现算法"""
    
    class ParamType(BaseModel):
        alpha: float = Field(0.05, description="显著性水平")
        indep_test: str = Field("fisherz", description="独立性检验方法")
        depth: int = Field(-1, description="条件集大小限制")
    
    def __call__(self, data, fields, params):
        # 转换数据格式
        np_data = self._to_numpy(data, fields)
        
        # 执行PC算法
        cg = pc(
            np_data,
            alpha=params.alpha,
            indep_test=fisherz,
            depth=params.depth,
            verbose=False
        )
        
        # 提取结果
        return {
            "graph": cg.G.graph.tolist(),  # 邻接矩阵
            "edges": self._extract_edges(cg),  # 边列表
            "nodes": [f.name for f in fields]
        }
    
    def _extract_edges(self, cg):
        """提取因果边"""
        edges = []
        n = len(cg.G.nodes)
        for i in range(n):
            for j in range(n):
                if cg.G.graph[i, j] != 0:
                    edge_type = self._get_edge_type(cg.G.graph[i, j])
                    edges.append({
                        "source": i,
                        "target": j,
                        "type": edge_type  # "->", "<-", "--"
                    })
        return edges
```

**调用示例**:
```python
import requests

# 调用PC算法进行因果发现
response = requests.post(
    "http://causal-service:5002/algo/PC/run",
    json={
        "dataSource": [
            {"marketing": 100, "season": 1, "sales": 500},
            {"marketing": 150, "season": 1, "sales": 600},
            # ... 更多数据
        ],
        "fields": [
            {"name": "marketing", "type": "quantitative"},
            {"name": "season", "type": "ordinal"},
            {"name": "sales", "type": "quantitative"}
        ],
        "params": {
            "alpha": 0.05,
            "indep_test": "fisherz"
        }
    }
)

result = response.json()
# result = {
#   "graph": [[0, 1, 0], [0, 0, 1], [0, 0, 0]],
#   "edges": [
#     {"source": "marketing", "target": "sales", "type": "->"},
#     {"source": "season", "target": "marketing", "type": "->"}
#   ]
# }
```

### 3.2 GES算法（贪婪等价搜索）

**原理**: 通过评分函数（如BIC）搜索最优因果图

**适用场景**:
- 数据量大（>1000样本）
- 需要评分比较不同因果模型
- 高斯分布假设成立

**核心思想**:
```
评分 = 模型拟合度 - 模型复杂度惩罚

GES算法：
1. 从空图开始
2. 贪婪地添加能提高评分的边
3. 贪婪地删除能降低评分的边
4. 贪婪地转向能提卅评分的边
5. 直到收敛
```

### 3.3 DoWhy因果推断

**原理**: 基于因果图进行干预效果估计

**核心能力**:
- **因果效应识别**: 自动识别可估计的因果效应
- **估计方法选择**: 支持多种估计器（倾向得分、工具变量等）
- **反驳检验**: 验证因果假设的稳健性

**代码示例**:
```python
# algorithms/dowhy_wrapper.py
import dowhy
from dowhy import CausalModel

class DoWhyWrapper(AlgoInterface):
    """DoWhy因果推断封装"""
    
    class ParamType(BaseModel):
        treatment: str      # 干预变量
        outcome: str        # 结果变量
        method: str = "backdoor.propensity_score_matching"
    
    def __call__(self, data, fields, params):
        # 创建因果模型
        model = CausalModel(
            data=data,
            treatment=params.treatment,
            outcome=params.outcome,
            graph=self._build_graph(fields)  # 从之前的发现结果
        )
        
        # 识别因果效应
        identified_estimand = model.identify_effect()
        
        # 估计因果效应
        estimate = model.estimate_effect(
            identified_estimand,
            method_name=params.method
        )
        
        # 反驳检验
        refutation = model.refute_estimate(
            identified_estimand,
            estimate,
            method_name="random_common_cause"
        )
        
        return {
            "causal_effect": estimate.value,  # 因果效应值
            "confidence_interval": estimate.get_confidence_intervals(),
            "refutation_result": refutation.refutation_result
        }
```

**What-if分析示例**:
```python
# 问：如果营销预算从100增加到150，销售额会如何？
response = requests.post(
    "http://causal-service:5002/algo/DoWhy/run",
    json={
        "dataSource": sales_data,
        "fields": fields,
        "params": {
            "treatment": "marketing",
            "outcome": "sales",
            "intervention": {"marketing": 150},  # 干预值
            "method": "backdoor.linear_regression"
        }
    }
)

result = response.json()
# result = {
#   "causal_effect": 25.5,  # 每增加1单位营销，销售增加25.5
#   "predicted_outcome": 638,  # 预计销售额
#   "confidence_interval": [620, 656]
# }
```

---

## 四、算法插件化设计

### 4.1 设计目标

- **易于扩展**: 新算法只需添加一个文件
- **统一接口**: 所有算法对外暴露相同API
- **参数自动生成**: 算法参数自动转为前端表单

### 4.2 核心抽象

```python
# algorithms/common.py
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Type, Any, Dict, List

class AlgoInterface(ABC):
    """算法接口基类 - 所有因果算法必须实现"""
    
    @property
    @abstractmethod
    def ParamType(self) -> Type[BaseModel]:
        """
        返回参数类型定义（Pydantic模型）
        用于：
        1. 参数校验
        2. 自动生成前端表单
        3. API文档生成
        """
        pass
    
    @abstractmethod
    def __call__(
        self,
        data: List[Dict],           # 原始数据
        fields: List[IFieldMeta],   # 字段元信息
        params: BaseModel           # 算法参数
    ) -> Dict[str, Any]:
        """
        执行算法
        
        Returns:
            必须包含以下字段：
            - success: bool
            - data: 算法结果
            - message: 可选的状态信息
        """
        pass
    
    def get_schema(self) -> Dict:
        """获取算法参数JSON Schema（用于前端）"""
        return self.ParamType.schema()


# 全局算法注册表
class AlgorithmRegistry:
    """算法注册中心"""
    
    DICT: Dict[str, AlgoInterface] = {}
    
    @classmethod
    def register(cls, name: str, algo: AlgoInterface):
        """注册算法"""
        cls.DICT[name] = algo
    
    @classmethod
    def get(cls, name: str) -> AlgoInterface:
        """获取算法实例"""
        return cls.DICT.get(name)
    
    @classmethod
    def list(cls) -> List[str]:
        """列出所有可用算法"""
        return list(cls.DICT.keys())

algorithms = AlgorithmRegistry()
```

### 4.3 如何实现新算法

**步骤1**: 创建算法文件
```python
# algorithms/my_algorithm.py
from .common import AlgoInterface
from pydantic import BaseModel, Field

class MyAlgorithm(AlgoInterface):
    """我的自定义因果算法"""
    
    # 定义参数
    class ParamType(BaseModel):
        learning_rate: float = Field(0.01, description="学习率")
        max_iter: int = Field(1000, description="最大迭代次数")
    
    def __call__(self, data, fields, params):
        # 实现算法逻辑
        result = self._my_algorithm_logic(data, params)
        
        return {
            "success": True,
            "data": result,
            "message": "算法执行成功"
        }
```

**步骤2**: 注册算法
```python
# algorithms/__init__.py
from .my_algorithm import MyAlgorithm

# 自动注册
algorithms.register("MyAlgo", MyAlgorithm())
```

**步骤3**: 立即可用
```python
# 前端自动获取到新算法
GET /algo/list
# 返回包含 "MyAlgo"

# 执行新算法
POST /algo/MyAlgo/run
```

---

## 五、API 参考

### 5.1 执行算法

```http
POST /algo/{algo_name}/run
Content-Type: application/json

{
  "dataSource": [...],      // 数据数组
  "fields": [...],          // 字段定义
  "params": {...}           // 算法参数
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "graph": [...],
    "edges": [...]
  },
  "message": "执行成功"
}
```

### 5.2 获取算法列表

```http
POST /algo/list
```

**响应**:
```json
{
  "PC": {
    "description": "PC因果发现算法",
    "parameters": {
      "alpha": {
        "type": "number",
        "default": 0.05,
        "description": "显著性水平"
      }
    }
  },
  "GES": {...},
  "DoWhy": {...}
}
```

### 5.3 健康检查

```http
GET /health
```

---

## 六、部署与配置

### 6.1 Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# causal-learn 和 DoWhy 是核心依赖
# requirements.txt:
# fastapi==0.104.1
# uvicorn==0.24.0
# causal-learn==0.1.3.3
# dowhy==0.9.1
# econml==0.14.0
# pandas==2.0.3
# numpy==1.24.3

COPY . .

EXPOSE 5002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5002"]
```

### 6.2 Docker Compose

```yaml
services:
  causal-service:
    build: ./services/causal-service
    network_mode: service:base
    environment:
      - CAUSAL_WORKERS=4  # 并行工作线程
      - MAX_DATA_SIZE=100000  # 最大数据行数
    deploy:
      resources:
        limits:
          cpus: '4'      # 因果分析耗CPU，多分配
          memory: 8G
```

### 6.3 性能优化

| 优化项 | 配置 | 效果 |
|--------|------|------|
| **并行计算** | `CAUSAL_WORKERS=4` | PC算法并行条件检验 |
| **数据采样** | 大数据集先采样 | 加速发现过程 |
| **缓存** | Redis缓存因果图 | 避免重复计算 |
| **超时控制** | 设置算法超时 | 防止长耗时任务 |

---

## 七、使用场景

### 场景1：营销ROI分析

```python
# 数据：营销费用、季节、销售额、竞品价格
data = [...]

# Step 1: 因果发现
graph = causal_discovery(data, algorithm="PC")
# 发现：季节 → 营销费用 → 销售额
#       竞品价格 → 销售额

# Step 2: 因果推断
effect = estimate_effect(
    data=data,
    graph=graph,
    treatment="marketing",
    outcome="sales"
)
# 结果：营销费用每增加1万，销售额增加2.5万（控制了季节因素）
```

### 场景2：产品功能归因

```python
# 分析哪些功能真正导致用户留存
data = [...]  # 功能使用数据 + 留存结果

# 发现因果图
graph = causal_discovery(data)
# 发现：功能A → 功能B → 留存
#       （功能A对留存只有间接影响）

# 决策：优先优化功能B，而非功能A
```

---

## 八、最佳实践

### 8.1 数据准备

- **样本量**: PC算法至少100样本，DoWhy至少1000样本
- **数据类型**: 数值型变量效果最好，类别变量需编码
- **缺失值**: 先填充或删除，大多数算法不支持缺失值

### 8.2 算法选择

| 场景 | 推荐算法 | 理由 |
|------|---------|------|
| 快速探索 | PC | 计算快，适合初步分析 |
| 大数据集 | GES | 评分搜索更稳定 |
| 非线性关系 | NOTEARS | 支持神经网络建模 |
| 时间序列 | Granger | 专门处理时序因果 |
| 干预估计 | DoWhy | 完整的推断框架 |

### 8.3 结果解读

- **相关 ≠ 因果**: 因果图只代表统计上的因果，不代表真实世界因果
- **混杂因素**: 总是考虑可能的混杂变量
- **反事实**: 因果推断的结果是对"平均"的估计，个体差异可能存在

---

## 九、与其他服务的关系

```
前端请求
    ↓
Nginx
    ↓
causal-service:5002
    ├── 需要数据？→ HTTP调用 connector:5001 查询
    ├── 需要预测？→ HTTP调用 prediction:5003 训练模型
    └── 结果 → 返回给前端
```

---

## 十、总结

causal-service 是 RATH 的核心差异化服务：

| 亮点 | 说明 |
|------|------|
| **算法丰富** | PC、GES、DoWhy等主流因果方法 |
| **插件化设计** | 易于扩展新算法 |
| **工程化** | FastAPI提供现代API体验 |
| **可视化** | 支持因果图渲染 |

**适用场景**:
- 需要区分相关性和因果性的分析场景
- 营销策略效果评估
- 产品功能归因分析
- 医疗/金融等需要严谨因果推断的领域

**参考文档**:
- [因果发现与因果推断通俗解释](../因果发现与因果推断通俗解释.md)
- [causal-learn文档](https://causal-learn.readthedocs.io/)
- [DoWhy文档](https://www.pywhy.org/dowhy/)
