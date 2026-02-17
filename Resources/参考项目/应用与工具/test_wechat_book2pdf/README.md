# 微信读书转 PDF 工具

基于 Playwright 的微信读书网页版抓取工具，自动截图并合并为 PDF。

## 功能特性

- **持久化登录**：首次扫码登录后，登录状态会保存到 `user_data` 目录，后续无需重复登录
- **自动章节翻页**：自动检测并点击「下一章」按钮，连续抓取整本书
- **高清截图**：采用 2x DPI 缩放，确保文字清晰
- **干净的页面**：自动隐藏顶栏、底栏、侧边栏等 UI 元素，只保留正文内容
- **自动合并 PDF**：截图完成后自动合并为单个 PDF 文件

## 安装

```bash
npm install
```

如果是首次使用 Playwright，还需要安装浏览器：

```bash
npx playwright install chromium
```

## 使用方法

1. **启动工具**

   ```bash
   node index.js
   ```

2. **登录微信读书**
   
   浏览器会自动打开微信读书首页。如果未登录，请扫码登录。登录状态会保存，下次无需重复扫码。

3. **进入目标书籍**
   
   在浏览器中手动导航到你想抓取的书籍，进入阅读器页面。

4. **开始抓取**
   
   在终端中按下 **回车键**，工具将开始自动抓取：
   - 逐屏截图当前章节
   - 自动跳转下一章
   - 重复直到全书结束（或达到 100 章上限）

5. **获取 PDF**
   
   抓取完成后，会在项目根目录生成 `book.pdf` 文件。

## 项目结构

```
test_wechat_book2pdf/
├── index.js          # 主程序
├── package.json      # 项目配置
├── user_data/        # 浏览器登录状态（自动生成）
└── book.pdf          # 输出的 PDF 文件（运行后生成）
```

## 技术细节

### 页面定位

微信读书使用 Canvas 渲染文字，核心容器的选择器为：

```javascript
const readerSelector = '.wr_canvasContainer';
```

### UI 清理

抓取前会自动隐藏以下元素，确保截图只包含正文：

- `.readerTopBar`：顶部导航栏
- `.readerControls`：阅读控制区
- `.readerFooter`：底部工具栏
- `.readerNotePanel`：笔记面板
- `.readerCatalogSideBar`：目录侧边栏

### 滚动与截图

每章按屏幕高度逐屏滚动，检测到滚动位置不变时判定为章节结束。截图前会等待 200ms 确保 Canvas 渲染完成。

## 注意事项

- **仅供个人学习使用**，请勿用于商业目的或侵犯版权
- 默认最多抓取 100 章，可在 `index.js` 中修改 `chapterCount > 100` 的限制
- 生成的 PDF 为图片格式，不支持文字选择

## 依赖

- [Playwright](https://playwright.dev/) - 浏览器自动化
- [pdf-lib](https://pdf-lib.js.org/) - PDF 生成与合并
