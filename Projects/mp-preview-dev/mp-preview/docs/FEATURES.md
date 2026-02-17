# 功能规格文档

本文档详细描述 MP Preview 插件的各项功能规格。

## 功能列表

| 功能 | 优先级 | 状态 | 说明 |
|------|--------|------|------|
| Markdown 预览 | P0 | ✅ | 实时预览 Markdown 渲染效果 |
| 模板切换 | P0 | ✅ | 提供多种预设样式模板 |
| 字体设置 | P0 | ✅ | 支持多种中文字体 |
| 字号调节 | P0 | ✅ | 调整正文字号 |
| 一键复制 | P0 | ✅ | 复制到公众号编辑器 |
| 锁定功能 | P1 | ✅ | 暂停实时预览 |
| 图片处理 | P1 | ✅ | 自动转 base64 |
| 背景设置 | P2 | ✅ | 自定义预览背景 |
| 数学公式 | P2 | 🚧 | 正在研究支持方案 |

---

## 功能详情

### 1. Markdown 预览

#### 功能描述
将当前打开的 Markdown 文件实时渲染为 HTML，并在侧边栏预览。

#### 用户场景
用户在编辑笔记时，可以实时看到最终渲染效果。

#### 实现细节
- 使用 Obsidian `MarkdownRenderer.render()` 进行渲染
- 渲染后对 DOM 进行后处理（`MPConverter`）
- 应用选中的模板样式（`TemplateManager`）

#### 触发条件
- 打开新文件
- 文件内容修改（防抖 500ms）
- 手动刷新（解锁时）

#### 异常处理
| 异常情况 | 处理方式 |
|----------|----------|
| 非 Markdown 文件 | 显示提示信息 |
| 文件读取失败 | 显示错误信息 |
| 渲染超时 | 显示加载提示 |

---

### 2. 模板系统

#### 功能描述
提供多种精心设计的排版模板，一键切换文章风格。

#### 预设模板

##### 2.1 默认模板 (default)
- **风格**：简洁现代
- **适用**：技术文章、教程
- **特点**：清晰的层级结构，适合长文阅读

##### 2.2 优雅模板 (elegant)
- **风格**：优雅复古
- **适用**：散文、随笔
- **特点**： serif 字体，增大行距，阅读舒适

##### 2.3 活力模板 (vibrant)
- **风格**：年轻活泼
- **适用**：营销文案、活动通知
- **特点**：鲜艳色彩，圆角设计

#### 模板结构
```typescript
interface Template {
    id: string;           // 唯一标识
    name: string;         // 显示名称
    description: string;  // 描述
    styles: {
        // 容器样式
        container: string;
        // 标题样式
        title: {
            h1: TitleStyle;
            h2: TitleStyle;
            h3: TitleStyle;
            base: TitleStyle;  // h4-h6
        };
        // 段落样式
        paragraph: string;
        // 列表样式
        list: {
            container: string;
            item: string;
            taskList: string;
        };
        // 引用样式
        quote: string;
        // 代码样式
        code: {
            header: {
                container: string;
                dot: string;
                colors: [string, string, string];  // 三个圆点颜色
            };
            block: string;   // 代码块
            inline: string;  // 行内代码
        };
        // 图片样式
        image: string;
        // 链接样式
        link: string;
        // 强调样式
        emphasis: {
            strong: string;  // 加粗
            em: string;      // 斜体
            del: string;     // 删除线
        };
        // 表格样式
        table: {
            container: string;
            header: string;
            cell: string;
        };
        // 分割线
        hr: string;
        // 脚注
        footnote: {
            ref: string;
            backref: string;
        };
    };
}
```

#### 样式生成规则
```typescript
// 标题样式示例
const titleStyle = {
    base: `
        position: relative;
        font-weight: bold;
        margin: 1.5em 0 0.8em;
    `,
    content: `
        position: relative;
        z-index: 1;
    `,
    after: `
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 8px;
        background: linear-gradient(...);
    `
};
```

---

### 3. 字体设置

#### 功能描述
支持切换不同的中文字体，确保文章显示效果。

#### 支持字体
| 字体名称 | 字体族 | 特点 |
|----------|--------|------|
| 系统默认 | -apple-system, sans-serif | 跨平台兼容 |
| 思源宋体 | 'Source Han Serif CN' | 专业印刷风格 |
| 思源黑体 | 'Source Han Sans CN' | 现代简洁 |
| 微软雅黑 | 'Microsoft YaHei' | Windows 默认 |
| 苹方 | 'PingFang SC' | macOS/iOS 默认 |
| 宋体 | 'SimSun' | 传统风格 |

#### 技术实现
```typescript
// 设置字体
setFont(fontFamily: string) {
    this.currentFont = fontFamily;
}

// 应用字体
applyFont(element: HTMLElement) {
    element.style.fontFamily = `${this.currentFont}, -apple-system, sans-serif`;
}
```

#### 加粗字体修复
**问题**：某些字体加粗后会回退到系统默认字体（如宋体）。

**解决方案**：
```typescript
element.querySelectorAll('strong').forEach(el => {
    el.setAttribute('style', 
        `${styles.emphasis.strong} font-family: ${this.currentFont} !important;`
    );
});
```

---

### 4. 字号调节

#### 功能描述
调整预览内容的正文字号。

#### 规格
- 范围：12px - 24px
- 步进：1px
- 默认：16px

#### 影响范围
- 正文段落
- 列表项
- 表格单元格
- 引用块

#### 不影响
- 标题（有独立的大小设置）
- 代码块（固定 14px）

---

### 5. 一键复制

#### 功能描述
将预览内容转换为适合微信公众号的格式，并复制到剪贴板。

#### 复制流程

```
┌─────────────┐
│  用户点击   │
│  复制按钮   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 1. 克隆 DOM 元素                        │
│    const clone = element.cloneNode(true)│
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 2. 处理图片                             │
│    - 遍历所有 <img>                     │
│    - fetch 图片资源                     │
│    - 转为 base64 DataURL                │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 3. 清理 HTML                            │
│    - 移除 data-* 属性                   │
│    - 移除 class 属性                    │
│    - 移除 id 属性                       │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ 4. 写入剪贴板                           │
│    - text/html 格式                     │
│    - text/plain 格式                    │
└─────────────────────────────────────────┘
```

#### 输出格式
```html
<!-- text/html -->
<section xmlns="http://www.w3.org/1999/xhtml" 
         style="font-size: 16px; font-family: 'PingFang SC'; ...">
    <!-- 内容 -->
</section>

<!-- text/plain -->
纯文本内容（去除所有 HTML 标签）
```

#### 图片处理
```typescript
async processImages(container: HTMLElement): Promise<void> {
    const images = container.querySelectorAll('img');
    
    for (const img of images) {
        if (img.src.startsWith('data:')) continue;
        
        try {
            const response = await fetch(img.src);
            const blob = await response.blob();
            const base64 = await this.blobToBase64(blob);
            img.src = base64;
        } catch (error) {
            console.error('图片转换失败:', error);
        }
    }
}
```

---

### 6. 锁定功能

#### 功能描述
暂停实时预览，避免编辑大文件时频繁刷新影响性能。

#### 交互设计
- 图标：🔒 / 🔓
- 提示：悬停显示当前状态
- 快捷键：可配置

#### 状态管理
```typescript
private isLocked: boolean = false;

 toggleLock() {
    this.isLocked = !this.isLocked;
    this.updateLockIcon();
}

onFileModify() {
    if (this.isLocked) return;  // 锁定时忽略更新
    this.scheduleUpdate();
}
```

#### 视觉反馈
- 锁定：图标变为 🔒，预览区域变暗
- 解锁：图标变为 🔓，预览区域正常

---

### 7. 背景设置

#### 功能描述
自定义预览区域的背景，模拟真实阅读环境。

#### 预设背景
| 背景 | 颜色值 | 适用场景 |
|------|--------|----------|
| 纯白 | #ffffff | 正式文档 |
| 护眼 | #f5f5dc | 长时间阅读 |
| 羊皮纸 | #f4ecd8 | 复古风格 |
| 夜间 | #2d2d2d | 暗色模式 |

#### 实现方式
```typescript
applyBackground(element: HTMLElement, background: string) {
    element.style.backgroundColor = background;
    element.style.backgroundImage = this.getBackgroundPattern(background);
}
```

---

## 待开发功能

### 数学公式支持 (P2)

#### 需求
支持 LaTeX 数学公式渲染，并能正确复制到公众号。

#### 技术难点
1. MathJax 渲染的 SVG 复制时容易丢失
2. 公众号对 SVG 支持有限
3. 需要找到可靠的转换方案

#### 可能的方案
1. 使用 html2canvas 将整个内容转为图片
2. 使用 KaTeX 重新渲染为 HTML
3. 将公式转为图片插入

### 自定义模板 (P3)

#### 需求
允许用户创建和保存自己的模板。

#### 实现思路
1. 提供模板编辑器界面
2. 支持 CSS 自定义
3. 导出/导入模板配置

---

## 兼容性

### 支持的 Markdown 语法

| 语法 | 支持状态 | 说明 |
|------|----------|------|
| 标题 | ✅ | h1-h6 全支持 |
| 段落 | ✅ | 自动换行 |
| 列表 | ✅ | 有序、无序、任务列表 |
| 代码 | ✅ | 代码块、行内代码 |
| 引用 | ✅ | 嵌套引用 |
| 表格 | ✅ | 基础表格 |
| 链接 | ✅ | 外部链接、内部链接 |
| 图片 | ✅ | 本地图片、网络图片 |
| 强调 | ✅ | 加粗、斜体、删除线 |
| 脚注 | ✅ | 基础支持 |
| 数学公式 | 🚧 | 开发中 |
| Mermaid | ❌ | 暂不支持 |
| 流程图 | ❌ | 暂不支持 |

### 浏览器兼容性
- Chrome/Edge: ✅
- Safari: ✅
- Firefox: ✅
