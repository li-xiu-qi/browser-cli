# RATH prediction：机器学习预测服务详解

**服务定位**: 自动化机器学习预测引擎  
**技术栈**: Python + FastAPI + scikit-learn + XGBoost  
**默认端口**: 5003  
**所属项目**: [RATH](https://github.com/Kanaries/RATH)

---

## 一、服务概述

### 1.1 什么是 prediction 服务？

prediction 服务提供**开箱即用的机器学习预测能力**，无需数据科学背景也能快速构建预测模型：

```
┌─────────────────────────────────────────────────────────────┐
│                    prediction :5003                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  输入数据                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  客户数据                                           │   │
│  │  ┌────┬────┬────┬────────┬──────────┐              │   │
│  │  │年龄│收入│性别│购买历史│ 是否流失  │ ← 目标变量  │   │
│  │  ├────┼────┼────┼────────┼──────────┤              │   │
│  │  │ 25 │ 5万 │ 男 │   3次   │   否     │              │   │
│  │  │ 35 │ 8万 │ 女 │   5次   │   否     │              │   │
│  │  │ 45 │ 3万 │ 男 │   1次   │   是     │              │   │
│  │  └────┴────┴────┴────────┴──────────┘              │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  prediction 服务                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. 自动特征工程                                      │   │
│  │ 2. 自动算法选择（分类/回归）                          │   │
│  │ 3. 自动超参数调优                                    │   │
│  │ 4. 模型评估与解释                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  输出                                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 模型准确率: 87%                                     │   │
│  │ 特征重要性: 收入 > 购买历史 > 年龄 > 性别             │   │
│  │ 预测结果: 新客户有 65% 概率会流失                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心能力

| 能力 | 说明 | 算法 |
|------|------|------|
| **分类** | 预测离散类别（是/否、A/B/C） | 随机森林、XGBoost、SVM |
| **回归** | 预测连续数值（价格、销量） | 线性回归、GBDT、神经网络 |
| **自动特征工程** | 自动处理缺失值、编码 | sklearn pipeline |
| **模型解释** | 特征重要性、SHAP值 | SHAP、Permutation Importance |
| **模型持久化** | 保存/加载训练好的模型 | joblib、pkl |

---

## 二、技术架构

### 2.1 项目结构

```
prediction/
├── main.py                 # FastAPI 入口
├── models.py              # Pydantic 模型定义
├── requirements.txt       # 依赖
├── Dockerfile            # 容器定义
├── classification/       # 分类算法
│   ├── __init__.py
│   ├── base.py           # 分类器基类
│   ├── random_forest.py
│   ├── xgboost_clf.py
│   ├── svm.py
│   └── logistic.py
├── regression/           # 回归算法
│   ├── __init__.py
│   ├── base.py           # 回归器基类
│   ├── linear.py
│   ├── ridge.py
│   ├── xgboost_reg.py
│   └── neural_network.py
├── preprocessing/        # 数据预处理
│   ├── __init__.py
│   ├── transform.py      # 特征转换
│   ├── encoder.py        # 编码器
│   └── imputer.py        # 缺失值填充
├── evaluation/           # 模型评估
│   ├── __init__.py
│   ├── metrics.py        # 评估指标
│   └── cross_validation.py
└── explainability/       # 可解释性
    ├── __init__.py
    └── shap_explainer.py
```

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     prediction :5003                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FastAPI Layer                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ POST /train              # 训练模型                 │   │
│  │ POST /predict            # 预测                     │   │
│  │ POST /evaluate           # 评估模型                 │   │
│  │ POST /explain            # 解释预测                 │   │
│  │ GET  /algorithms         # 列出算法                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  Task Router                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 根据目标变量类型自动路由：                           │   │
│  │ - 类别数=2 → 二分类                                  │   │
│  │ - 类别数>2 → 多分类                                  │   │
│  │ - 连续值 → 回归                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  Pipeline                                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ Preprocess  │ │   Train     │ │  Evaluate   │          │
│  │ 预处理      │ │   训练      │ │   评估      │          │
│  │             │ │             │ │             │          │
│  │ - 缺失值    │ │ - 算法选择  │ │ - 准确率    │          │
│  │ - 编码      │ │ - 超参数    │ │ - F1/P/R    │          │
│  │ - 标准化    │ │ - 交叉验证  │ │ - MSE/RMSE  │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、核心算法详解

### 3.1 分类算法

#### 随机森林分类器

```python
# classification/random_forest.py
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
from .base import BaseClassifier

class RandomForestClassifier(BaseClassifier):
    """随机森林分类器"""
    
    name = "random_forest"
    display_name = "随机森林"
    
    # 默认超参数
    default_params = {
        'n_estimators': 100,
        'max_depth': 10,
        'min_samples_split': 2,
        'min_samples_leaf': 1,
        'random_state': 42
    }
    
    # 可搜索的超参数空间
    param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [5, 10, 20, None],
        'min_samples_split': [2, 5, 10]
    }
    
    def fit(self, X, y, tune_hyperparams=False):
        """训练模型"""
        if tune_hyperparams:
            # 使用网格搜索优化超参数
            grid_search = GridSearchCV(
                RandomForestClassifier(random_state=42),
                self.param_grid,
                cv=5,
                scoring='accuracy',
                n_jobs=-1
            )
            grid_search.fit(X, y)
            self.model = grid_search.best_estimator_
            self.best_params = grid_search.best_params_
        else:
            # 使用默认参数
            self.model = RandomForestClassifier(**self.default_params)
            self.model.fit(X, y)
        
        # 记录特征重要性
        self.feature_importance = self.model.feature_importances_
        
        return self
    
    def predict(self, X):
        """预测类别"""
        return self.model.predict(X)
    
    def predict_proba(self, X):
        """预测概率"""
        return self.model.predict_proba(X)
```

#### XGBoost分类器

```python
# classification/xgboost_clf.py
import xgboost as xgb
from .base import BaseClassifier

class XGBoostClassifier(BaseClassifier):
    """XGBoost分类器 - 通常效果更好但需要调参"""
    
    name = "xgboost"
    display_name = "XGBoost"
    
    default_params = {
        'n_estimators': 100,
        'max_depth': 6,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42
    }
    
    def fit(self, X, y, tune_hyperparams=False):
        """训练模型"""
        self.model = xgb.XGBClassifier(**self.default_params)
        self.model.fit(X, y)
        
        self.feature_importance = self.model.feature_importances_
        return self
```

### 3.2 回归算法

#### 梯度提升回归

```python
# regression/xgboost_reg.py
from sklearn.ensemble import GradientBoostingRegressor
from .base import BaseRegressor

class GBDTRegressor(BaseRegressor):
    """梯度提升回归树"""
    
    name = "gbdt"
    display_name = "梯度提升树"
    
    default_params = {
        'n_estimators': 100,
        'max_depth': 4,
        'learning_rate': 0.1,
        'loss': 'squared_error'
    }
    
    def fit(self, X, y):
        self.model = GradientBoostingRegressor(**self.default_params)
        self.model.fit(X, y)
        self.feature_importance = self.model.feature_importances_
        return self
    
    def predict(self, X):
        return self.model.predict(X)
```

### 3.3 基类设计

```python
# classification/base.py
from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any

class BaseClassifier(ABC):
    """分类器基类"""
    
    name: str = None  # 算法标识
    display_name: str = None  # 显示名称
    model = None
    feature_importance = None
    
    @abstractmethod
    def fit(self, X, y, tune_hyperparams=False):
        """训练模型"""
        pass
    
    @abstractmethod
    def predict(self, X):
        """预测类别"""
        pass
    
    @abstractmethod
    def predict_proba(self, X):
        """预测概率"""
        pass
    
    def get_feature_importance(self, feature_names=None) -> Dict[str, float]:
        """获取特征重要性"""
        if self.feature_importance is None:
            return {}
        
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(len(self.feature_importance))]
        
        return dict(zip(feature_names, self.feature_importance))
    
    def save(self, path: str):
        """保存模型"""
        import joblib
        joblib.dump(self.model, path)
    
    def load(self, path: str):
        """加载模型"""
        import joblib
        self.model = joblib.load(path)
        return self


# regression/base.py
class BaseRegressor(ABC):
    """回归器基类"""
    
    name: str = None
    display_name: str = None
    model = None
    feature_importance = None
    
    @abstractmethod
    def fit(self, X, y):
        """训练模型"""
        pass
    
    @abstractmethod
    def predict(self, X):
        """预测数值"""
        pass
    
    def get_feature_importance(self, feature_names=None) -> Dict[str, float]:
        """获取特征重要性"""
        if self.feature_importance is None:
            return {}
        
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(len(self.feature_importance))]
        
        return dict(zip(feature_names, self.feature_importance))
```

---

## 四、数据预处理流水线

### 4.1 完整的预处理流程

```python
# preprocessing/transform.py
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.impute import SimpleImputer
import pandas as pd
import numpy as np

class DataTransformer:
    """数据转换器 - 自动处理各种数据类型"""
    
    def __init__(self):
        self.numeric_features = []
        self.categorical_features = []
        self.target_encoder = None
        self.preprocessor = None
    
    def fit(self, df: pd.DataFrame, target_column: str):
        """
        学习数据转换
        
        Args:
            df: 数据框
            target_column: 目标变量列名
        """
        # 分离特征和目标
        X = df.drop(columns=[target_column])
        y = df[target_column]
        
        # 自动识别数据类型
        self.numeric_features = X.select_dtypes(
            include=[np.number]
        ).columns.tolist()
        
        self.categorical_features = X.select_dtypes(
            include=['object', 'category']
        ).columns.tolist()
        
        # 构建预处理流水线
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),  # 数值缺失用中位数
            ('scaler', StandardScaler())  # 标准化
        ])
        
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),  # 类别缺失用'missing'
            ('encoder', OneHotEncoder(handle_unknown='ignore'))  # One-Hot编码
        ])
        
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, self.numeric_features),
                ('cat', categorical_transformer, self.categorical_features)
            ]
        )
        
        # 拟合预处理
        self.preprocessor.fit(X)
        
        # 处理目标变量
        if y.dtype == 'object' or y.dtype.name == 'category':
            self.target_encoder = LabelEncoder()
            self.target_encoder.fit(y)
        
        return self
    
    def transform(self, df: pd.DataFrame, target_column: str = None):
        """
        转换数据
        
        Returns:
            X_processed, y_processed (如果提供了target_column)
        """
        if target_column:
            X = df.drop(columns=[target_column])
            y = df[target_column]
            
            # 转换特征
            X_processed = self.preprocessor.transform(X)
            
            # 转换目标
            if self.target_encoder:
                y_processed = self.target_encoder.transform(y)
            else:
                y_processed = y.values
            
            return X_processed, y_processed
        else:
            # 只转换特征（预测时）
            return self.preprocessor.transform(df)
    
    def get_feature_names(self):
        """获取转换后的特征名"""
        feature_names = []
        
        # 数值特征
        feature_names.extend(self.numeric_features)
        
        # 类别特征（展开One-Hot编码后的名称）
        cat_encoder = self.preprocessor.named_transformers_['cat']['encoder']
        cat_features = cat_encoder.get_feature_names_out(self.categorical_features)
        feature_names.extend(cat_features)
        
        return feature_names
```

---

## 五、API 设计

### 5.1 训练模型

```python
# main.py
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import pandas as pd

app = FastAPI(title="RATH Prediction Service")

class TrainRequest(BaseModel):
    data: List[Dict[str, Any]]  # 训练数据
    target: str                 # 目标变量名
    algorithm: str = Field("auto", description="算法名称或auto自动选择")
    tune_hyperparams: bool = False  # 是否调优超参数
    test_size: float = 0.2      # 测试集比例
    
class TrainResponse(BaseModel):
    success: bool
    model_id: str              # 模型唯一ID
    task_type: str             # "classification" 或 "regression"
    algorithm_used: str        # 实际使用的算法
    metrics: Dict[str, float]  # 评估指标
    feature_importance: Dict[str, float]  # 特征重要性
    message: str

@app.post("/train", response_model=TrainResponse)
async def train_model(request: TrainRequest):
    """训练机器学习模型"""
    try:
        # 转换为DataFrame
        df = pd.DataFrame(request.data)
        
        # 自动判断任务类型
        target = df[request.target]
        if target.dtype == 'object' or target.nunique() < 10:
            task_type = "classification"
            n_classes = target.nunique()
        else:
            task_type = "regression"
            n_classes = None
        
        # 数据预处理
        transformer = DataTransformer()
        transformer.fit(df, request.target)
        X, y = transformer.transform(df, request.target)
        
        # 划分训练集和测试集
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=request.test_size, random_state=42
        )
        
        # 选择算法
        algorithm = request.algorithm
        if algorithm == "auto":
            algorithm = select_best_algorithm(task_type, X_train, y_train)
        
        # 获取算法实例
        model = get_algorithm(algorithm, task_type)
        
        # 训练
        model.fit(X_train, y_train, tune_hyperparams=request.tune_hyperparams)
        
        # 评估
        metrics = evaluate_model(model, X_test, y_test, task_type)
        
        # 保存模型
        model_id = save_model(model, transformer, algorithm)
        
        # 特征重要性
        feature_names = transformer.get_feature_names()
        importance = model.get_feature_importance(feature_names)
        
        return TrainResponse(
            success=True,
            model_id=model_id,
            task_type=task_type,
            algorithm_used=algorithm,
            metrics=metrics,
            feature_importance=importance,
            message="模型训练成功"
        )
        
    except Exception as e:
        return TrainResponse(
            success=False,
            model_id="",
            task_type="",
            algorithm_used="",
            metrics={},
            feature_importance={},
            message=str(e)
        )

def select_best_algorithm(task_type, X, y):
    """自动选择最佳算法"""
    if task_type == "classification":
        # 简单规则：小数据集用随机森林，大数据集用XGBoost
        if X.shape[0] < 1000:
            return "random_forest"
        else:
            return "xgboost"
    else:
        return "gbdt"

def evaluate_model(model, X_test, y_test, task_type):
    """评估模型性能"""
    from sklearn import metrics
    
    y_pred = model.predict(X_test)
    
    if task_type == "classification":
        return {
            "accuracy": metrics.accuracy_score(y_test, y_pred),
            "precision": metrics.precision_score(y_test, y_pred, average='weighted'),
            "recall": metrics.recall_score(y_test, y_pred, average='weighted'),
            "f1": metrics.f1_score(y_test, y_pred, average='weighted')
        }
    else:
        return {
            "mse": metrics.mean_squared_error(y_test, y_pred),
            "rmse": metrics.mean_squared_error(y_test, y_pred, squared=False),
            "mae": metrics.mean_absolute_error(y_test, y_pred),
            "r2": metrics.r2_score(y_test, y_pred)
        }
```

### 5.2 预测

```python
class PredictRequest(BaseModel):
    model_id: str              # 模型ID
    data: List[Dict[str, Any]] # 待预测数据

class PredictResponse(BaseModel):
    success: bool
    predictions: List[Any]     # 预测结果
    probabilities: Optional[List[Dict[str, float]]]  # 分类概率
    message: str

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """使用训练好的模型进行预测"""
    try:
        # 加载模型
        model, transformer = load_model(request.model_id)
        
        # 转换数据
        df = pd.DataFrame(request.data)
        X = transformer.transform(df)
        
        # 预测
        predictions = model.predict(X)
        
        # 分类任务返回概率
        probabilities = None
        if hasattr(model, 'predict_proba'):
            probs = model.predict_proba(X)
            class_names = model.model.classes_
            probabilities = [
                {str(cls): float(prob) for cls, prob in zip(class_names, row)}
                for row in probs
            ]
        
        return PredictResponse(
            success=True,
            predictions=predictions.tolist(),
            probabilities=probabilities,
            message="预测成功"
        )
        
    except Exception as e:
        return PredictResponse(
            success=False,
            predictions=[],
            message=str(e)
        )
```

### 5.3 解释预测（SHAP）

```python
# explainability/shap_explainer.py
import shap
import numpy as np

def explain_prediction(model, X, feature_names):
    """
    使用SHAP解释预测结果
    
    Returns:
        每个样本的SHAP值
    """
    # 创建SHAP解释器
    explainer = shap.TreeExplainer(model.model)
    shap_values = explainer.shap_values(X)
    
    explanations = []
    for i, sample_shap in enumerate(shap_values):
        # 取绝对值最大的前5个特征
        top_features_idx = np.argsort(np.abs(sample_shap))[-5:][::-1]
        
        explanation = {
            "sample_index": i,
            "top_features": [
                {
                    "feature": feature_names[idx],
                    "contribution": float(sample_shap[idx]),
                    "direction": "increase" if sample_shap[idx] > 0 else "decrease"
                }
                for idx in top_features_idx
            ]
        }
        explanations.append(explanation)
    
    return explanations

@app.post("/explain")
async def explain(request: PredictRequest):
    """解释预测结果"""
    model, transformer = load_model(request.model_id)
    df = pd.DataFrame(request.data)
    X = transformer.transform(df)
    feature_names = transformer.get_feature_names()
    
    explanations = explain_prediction(model, X, feature_names)
    
    return {"success": True, "explanations": explanations}
```

---

## 六、使用示例

### 6.1 训练分类模型

```python
import requests

# 1. 训练客户流失预测模型
response = requests.post("http://prediction:5003/train", json={
    "data": [
        {"age": 25, "income": 50000, "tenure": 2, "churn": 0},
        {"age": 35, "income": 80000, "tenure": 5, "churn": 0},
        {"age": 45, "income": 30000, "tenure": 1, "churn": 1},
        # ... 更多数据
    ],
    "target": "churn",
    "algorithm": "xgboost",  # 或 "auto" 自动选择
    "tune_hyperparams": True
})

result = response.json()
print(result)
# {
#   "success": true,
#   "model_id": "model_1699123456",
#   "task_type": "classification",
#   "algorithm_used": "xgboost",
#   "metrics": {
#     "accuracy": 0.87,
#     "precision": 0.85,
#     "recall": 0.83,
#     "f1": 0.84
#   },
#   "feature_importance": {
#     "tenure": 0.45,
#     "income": 0.30,
#     "age": 0.25
#   }
# }
```

### 6.2 预测新客户

```python
# 2. 预测新客户是否会流失
response = requests.post("http://prediction:5003/predict", json={
    "model_id": "model_1699123456",
    "data": [
        {"age": 28, "income": 60000, "tenure": 1}
    ]
})

result = response.json()
print(result)
# {
#   "success": true,
#   "predictions": [1],  # 1表示会流失
#   "probabilities": [{"0": 0.32, "1": 0.68}]  # 68%概率流失
# }
```

### 6.3 解释预测

```python
# 3. 解释为什么预测会流失
response = requests.post("http://prediction:5003/explain", json={
    "model_id": "model_1699123456",
    "data": [
        {"age": 28, "income": 60000, "tenure": 1}
    ]
})

result = response.json()
print(result)
# {
#   "explanations": [{
#     "sample_index": 0,
#     "top_features": [
#       {"feature": "tenure", "contribution": 0.35, "direction": "increase"},
#       {"feature": "income", "contribution": -0.15, "direction": "decrease"},
#       {"feature": "age", "contribution": 0.05, "direction": "increase"}
#     ]
#   }]
# }
# 解释：tenure=1（使用时间短）是主要流失原因，income=60000（收入高）是保护因素
```

---

## 七、部署与配置

### 7.1 Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# requirements.txt:
# fastapi==0.104.1
# uvicorn==0.24.0
# scikit-learn==1.3.2
# xgboost==2.0.2
# pandas==2.0.3
# numpy==1.24.3
# shap==0.44.0

COPY . .

EXPOSE 5003

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5003"]
```

### 7.2 模型持久化

```python
# model_storage.py
import os
import joblib
import uuid
from datetime import datetime

MODEL_DIR = "/app/models"

def save_model(model, transformer, algorithm):
    """保存模型到磁盘"""
    model_id = f"model_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
    model_path = os.path.join(MODEL_DIR, f"{model_id}.pkl")
    
    joblib.dump({
        "model": model,
        "transformer": transformer,
        "algorithm": algorithm,
        "created_at": datetime.now().isoformat()
    }, model_path)
    
    return model_id

def load_model(model_id):
    """从磁盘加载模型"""
    model_path = os.path.join(MODEL_DIR, f"{model_id}.pkl")
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"模型不存在: {model_id}")
    
    data = joblib.load(model_path)
    return data["model"], data["transformer"]
```

---

## 八、总结

prediction 服务是 RATH 的智能预测引擎：

| 亮点 | 说明 |
|------|------|
| **开箱即用** | 无需ML知识，API调用即可 |
| **自动处理** | 数据清洗、特征工程、模型选择全自动 |
| **可解释** | SHAP值解释预测原因 |
| **生产就绪** | 模型持久化、快速预测 |

**适用场景**:
- 客户流失预测
- 销售预测
- 风险评估
- 任何有历史数据的分类/回归问题

**借鉴价值**: ⭐⭐⭐⭐
- 学习AutoML的简单实现
- 特征工程流水线设计
- 模型服务化部署
