---
title: "抛弃MCP，Skills，我们率先落地第三代工具架构 Tool Market"
source: "https://mp.weixin.qq.com/s/ZNBFC1OVvVhgmCjDUtdBqQ?scene=1&click_id=9"
author:
  - "[[Mong]]"
published:
created: 2026-02-08
description: "做你自己问题的导演。"
tags:
  - "clippings"
---
原创 Mong *2026年2月6日 19:05*

## 写在最前面：这篇文章是给谁看的

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/iaaO3sE95o90iaXbGMbTcLgLfX39GtwgDQwuA7DAGMo4K8AibBvudMors3p2pe5ZNhFLvR37UN21mquVsEUjDSNLg/640?wx_fmt=png&from=appmsg&watermark=1&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=0)


**如果你：**

1.听说过 ChatGPT、Agent 这些词，但不太清楚它们跟"工具"有什么关系

2.看到 MCP、Skills 人人都在聊，但到底是什么？

3.或者你就是好奇，想从零开始搞明白这件事

4.MCP、Skills 都是先驱，为什么 Command Tools 才是终极进化？

那这篇文章就是为你写的。

先搞清楚，AI 为什么需要"工具"

## AI 不是万能的，它有很多事做不了

你可能用过 ChatGPT、豆包、Deepseek 这些聊天 AI。它们能回答问题、写文章、写代码，但有很多事做不了：

> -   你让它帮你发一封邮件—— 它只能写内容，但发不出去
>     
> 
> -   你让它帮你在电脑上创建一个文件—— 它只能告诉你命令，但自己创建不了
>     

为什么做不到？因为 AI 本质上只是一个"语言模型" 。它的能力是"理解文字"和"生成文字"。它没有手、没有脚、没有眼睛、没有网络连接。 它就像一个被关在房间里的超级聪明的人 ，只能通过纸条交流，没有手脚、没有网络连接。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/iaaO3sE95o91F9Wa5Teo5Szk3KBSuibJ4OtEVaSDtxjugU1xKlQnOU1ZxGhdHdDXPZPYIibdC9SrQSKuV5695icbXA/640?wx_fmt=png&from=appmsg&watermark=1&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=1)

这个人再聪明，他也没法帮你去超市买菜，对吧？因为他出不去。

通常大家看到的诸如豆包、Deepseek，都只有有限的几个预置工具，完成人们已经设计好的能力，比如Deepseek 和豆包都有联网搜索的能力。联网搜索就是工具。

所以我们需要给 AI 配"工具"

怎么让这个被关在房间里的聪明人能做更多事情呢？ **答案是：给他配工具。 比如：**

> -   给他一部电话，他就能打电话了
>     
> -   给他一台能上网的电脑，他就能查天气了
>     
> -   给他一个机械臂，他就能帮你按按钮了
>     

同样的道理，我们给 AI 配"工具"，AI 就能做更多事情了。

![飞书文档 - 图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

通常大家看到的 Deepseek、豆包都只有有限的几个预置工具，比如联网搜索。问题是： **这些工具怎么做？怎么让 AI 能用上？**

AI调用工具的进化之路：三种思路，三种答案

## 在"怎么给 AI 做工具"这件事上，业界有三个进化方向：MCP、Skills、Command Tools。

### 一个比喻：你要教一个外星人使用地球上的工具

想象你要教一个超级聪明但对地球一无所知的外星人使用工具。


**思路一：把工具和说明一股脑儿给他（MCP）**

你说："地球上有很多商店，你先学会怎么去商店、怎么跟店员沟通、怎么付钱。"

外星人买回一堆工具，但问题来了：

-   他买回来一把锤子，不知道怎么用
    
-   他买回来一个电饭煲，不知道怎么用
    
-   他背着一堆工具负重前行，还要记住所有使用说明
    
-   没人告诉他使用的最佳实践，也没人告诉他怎么组合使用
    

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

这就是 **MCP** **的思路：它解决的是"怎么连接和调用工具"的问题** 。

但它有三个硬伤：

1\. 要求一次性加载所有工具信息（脑子容易爆）

2\. 还要求工具以"服务"形式常驻运行（资源消耗大）。

3\. 只是解释工具怎么用，没有实际场景的最佳实践，没有跨工具的组合使用说明。


**思路二：先教他"工具能干什么，怎么干才是最好的"（Skills）**

你说："工具分几类。有'切东西'的能力，有'煮东西'的能力……而且我还会告诉你切东西的最佳实践：先洗菜、再切丝、刀要这样握才安全……"

外星人明白了工具分类和方法论。而且他可以需要什么临时拿什么，不用背着一堆工具。但具体用什么切？切完放哪？方法论怎么落地成具体操作？还是不太清楚。

这就是 **Skills 的思路：它解决的是"能力的抽象描述"和"方法论/** **最佳实践** **"问题。 支持渐进式加载。**

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

但是 Skills 的缺点也非常明显：

-   组织形态松散， 实际上就是一个目录文件夹，工具和文档依然分散 。
    
-   难以迁移和分发， 依赖特定环境（比如 Python 3.10、本地路径等）
    

思路三：直接给他一套打包好的工具，每个工具都附带详细说明书（Command Tool）

你说："来，这个盒子给你。里面有把菜刀，点 help 按钮就会教你怎么握、怎么切、切完怎么洗。还有个电饭煲，点 help 教你怎么插电、怎么放米、怎么按按钮。这些工具还可以组合使用——先用刀把菜切好，再用电饭煲把饭煮好。"

外星人拿到后，一步步操作，很快就学会了。而且他发现，这些工具可以组合起来用，非常灵活。

这就是 **Command Tools 的思路：它把工具做成"可以直接发货的产品"，每个产品都自带说明书，产品之间还能组合使用** 。而且可以分发，放到任何一台机器上都可以被人或 AI 直接使用。此外，世界上早已存在大量的 Command Tool，每个都有 \--help 按钮，相当于一个简单的 Skill，而且是渐进式披露。

  

## MCP：解决"连接"问题，但有局限

### MCP 是什么？

MCP（Model Context Protocol，模型上下文协议）是一套规则，规定了：

-   AI 怎么发现有哪些工具可以用
    
-   AI 怎么告诉工具"我要用你"
    
-   请求和返回的格式是什么样
    
      
    


**核心价值** ：统一了 AI 和工具的"沟通方式"。就像全世界都说英语，你只要学会英语，就能跟全世界的人沟通。

### MCP 的局限在哪？

MCP 解决了"连接"和"调用"的问题。但它还有下面这些局限：


**问题一：工具一多，AI 的"** **脑容量** **"就不够了**


**AI 有"上下文窗口"限制——能同时记住的信息量有限。MCP 要求把所有工具的说明一次性全部塞给 AI。**

假设你有 100 个工具，每个工具说明 500 字，那就是 50000 字...... AI 的上下文窗口被工具说明塞满了，根本没有空间留给你的实际问题。

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

MCP 没有"渐进式披露"设计——不支持"先告诉 AI 有哪些工具，等真正需要时再详细介绍"。


**问题二：工具必须以"服务"形式常驻运行，资源消耗大**

MCP 要求工具以"服务"的形式一直运行着，等待 AI 调用。就像你家里有 10 个佣人 24 小时待着，即使今天一整天都没让他们干活，他们也在那儿消耗资源。这带来两个麻烦：

-   一堆后台进程占用内存和 CPU
    
-   要装各种运行环境（Node.js、Python、Go……），你的电脑变成"运行时动物园"
    

  

问题三：只解释工具怎么用，没有 **最佳实践** **和组合说明**

MCP 只规定"沟通格式"，但不管：

-   这个工具在什么场景下最好用？
    
-   怎么用这个工具效果最好？
    
-   多个工具怎么组合起来完成复杂任务？
    
      
    


**所以，** **MCP** **很重要，但它只是"必要条件"，不是"充分条件"。** 用人话说：有了 MCP，AI 能连上工具了，但能不能用好工具，那是另一回事。

## Skills：解决"工具能干什么"的问题，但难以分发

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

### Skills 是什么？

Skills 指"一种能力的抽象描述"，比如"发邮件"、"查天气"、"生成代码"都是 skill。


**核心价值** ：

1.  **抽象和表达** ：说"发邮件"三个字，大家就都懂了，不需要关心具体用哪个邮件服务、什么协议
    
2.  **提供方法论和最佳实践** ：不只说"能做什么"，还告诉你"怎么做才对"——写代码前应该先做什么、写代码时要注意什么、写完之后要做什么、有哪些常见的坑要避免
    

### Skills 的问题


**问题一：目录结构虽有规范，但过于灵活**

Skills 通常会有一套目录结构规范，比如：

```js
my_skill/├── README.md          # 技能目录列表└── skill01/            # 技能目录     ├── SKILL.md      # 技能1└── skill02/            # 技能目录          ├── SKILL.md      # 技能2     |── run.py        # 技能2的工具└── skill03/            # 技能目录     ├── SKILL.md      # 技能3└── ...
```

但这个技能很难发布，除非是纯文本的技能。而且 Skill 里经常依赖本地环境和目录。


**问题二：工具和技能是分开的**

这是一个更根本的问题。在 Skills 体系里， **"工具"和"使用工具的技能"是两个分开的东西** 。

在 Skills 体系里，"工具"（实际能执行的程序）和"技能"（告诉 AI 怎么用的说明）是两个分开的东西。

你拿到一个 skill（技能说明），不一定能拿到对应的工具；你拿到一个工具，不一定能拿到对应的 skill（使用方法论）。


**问题三：分发困难（这是最重要的问题）**

假设我想把我写的 skill 分享给你。我得：

1.  把代码发给你
    
2.  告诉你要用什么版本的 Python
    
3.  告诉你要安装哪些库
    
4.  告诉你怎么配置环境变量
    
5.  告诉你怎么运行
    

太麻烦了。很多时候，你按照我的说明做了，还是跑不起来，因为你的电脑环境和我的不一样。


**所以，Skills 作为"思考方式"有价值，但很难形成一个大家都能用、都能传、都能组合的工具生态。**

## Command Tools：把能力变成"可以发货的产品"

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

### Command Tools 是什么？

Command Tools（命令行工具）的核心思想是： **把"能力"做成一个可执行的命令** 。

> 比如：
> 
> -   把"发邮件"能力做成 `send-email` 命令
>     
> -   把"查天气"能力做成 `weather` 命令
>     
> -   把"生成代码"能力做成 `gen-code` 命令
>     

### Command Tools 好在哪？

#### 优势一：可执行

Command Tool 是一个可以直接运行的东西。你双击它（或者在命令行里输入它的名字），它就运行了。不需要额外的东西。

对比 Skills：Skills 除了文本，一般包含的可执行工具往往只是一段代码，你要运行它，得先有 Python 环境，得安装各种依赖库，得配置各种环境变量，才能跑起来。

Command Tool 把这些都打包好了，给你一个"制品"（做好的成品），你拿来就能用。

#### 优势二：自带说明书（--help）

几乎所有的 Command Tool 都支持一个特殊的参数： `--help` 。你输入 `工具名 --help` ，它就会打印出这个工具的使用说明。比如：

```js
$ gen-code --helpUsage: gen-code [OPTIONS] DESCRIPTIONGenerate code based on natural language description.Options:  --language TEXT   Programming language (default: python)  --output TEXT     Output file path  --help            Show this message and exit.
```

-   这个工具是干什么的（Generate code based on natural language description）
    
-   怎么用它（ `gen-code [OPTIONS] DESCRIPTION` ）
    
-   有哪些参数可以传（ `--language` 、 `--output` ）
    
-   每个参数是什么意思
    
      
    


**这就是"自带说明书"。** 你不需要去找额外的文档，不需要去问别人，输入 `--help` 就能知道怎么用。

#### 好处三：还可以有 --skill（给 AI 看的升级版说明书）

这是一个更进阶的设计。 `--help` 是给人看的说明书，它用的是人类语言，格式也是人类习惯的格式。但 AI 不是人类。AI 更喜欢"结构化"的信息。


**\--skill 就是输出这种结构化说明的参数。**

> 当 AI 想了解一个工具怎么用时，它可以调用 `工具名 --skill` ，拿到结构化的说明，然后就能准确地知道该传什么参数、怎么调用这个工具。

你可以把 `--help` 和 `--skill` 理解为：

-   `--help` ：给人看的说明书（用人话写，方便人阅读）
    
-   `--skill` ：给 AI 看的说明书（用结构化格式写，方便 AI 解析）
    
      
    

#### 好处四：有版本号

> Command Tool 是一个制品，制品可以有版本号：  
> 
> -   1.0.0 版本发布了
>     
> -   发现了 bug，修复后发布 1.0.1 版本
>     
> -   加了新功能，发布 1.1.0 版本
>     

有版本号意味着：可以升级、可以回滚、可以追溯。

#### 好处五：能分发（最重要）

> **Command Tool 可以非常容易地分发：**
> 
> -   我把一个 exe 文件发给你，你就能用了
>     
> -   速度极快，因为是二进制文件， 不需要编译，不需要安装环境，直接运行
>     


**一份制品，到处能跑** 。

### 一个公式：Command Tool = Skill + Command

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

> \- **Skill** 是"能力"，是"能做什么"，怎么做，最佳流程和实践
> 
> \- **Command** 是"命令"，是"怎么调用"

Command Tool 把"能力"和"调用方式"打包在一起，变成一个完整的、可以发货的产品。

## 渐进式披露：AI 不需要一次知道所有

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

### 什么是"渐进式披露"？

### 渐进式披露就是"一步一步告诉你，而不是一次性全部告诉你"。

就像电视说明书：第一页告诉你怎么开机，开机后屏幕上有引导告诉你怎么连 WiFi，连上 WiFi 后引导告诉你怎么搜台……你用到什么，它就教你什么。

Command Tools 通过"子命令"实现渐进式披露

有些工具功能很多，它会把功能分成几个"子命令"。

> 比如 `git` 这个工具：
> 
> -   `git clone` 是"克隆仓库"
>     
> -   `git add` 是"添加文件"
>     
> -   `git commit` 是"提交更改"
>     
> -   `git push` 是"推送到远程"
>     
> 
> `clone` 、 `add` 、 `commit` 、 `push` 都是 `git` 的子命令。你不需要一次性知道 git 的所有功能。你可以先输入 `git --help` ，看到它有哪些子命令。然后当你需要克隆仓库时，再输入 `git clone --help` ，专门看克隆怎么用。

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

这对 AI 有什么好处？

对 AI 来说，渐进式披露太重要了。想象一下，如果 AI 要用一个工具，它得先把这个工具的所有功能、所有参数、所有用法都加载到脑子里，然后才能开始工作。

有了渐进式披露，AI 的工作方式就变了：

01

第一步：看大纲

AI 先问："你这个工具能干什么？"

工具回答："我有这些子命令：create、delete、update、query。"

AI 记下：哦，这个工具能创建、删除、更新、查询。

02

第二步：按需深入

AI 接到一个任务："帮用户查一下订单。"

AI 想：我需要用"查询"功能。

AI 问："query 子命令怎么用？"

工具回答（通过 `--skill` ）："query 需要这些参数：order\_id（必填），format（可选，默认 json）。"

03

第三步：精准执行

AI 现在知道怎么调用了。它执行： `工具名 query --order_id=12345` 拿到结果，返回给用户。

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

看到了吗？AI 从头到尾只学习了它需要的那一部分（query 子命令）。 **这就是渐进式披露的威力：AI 按需学习，效率更高，出错更少。**

## 组合的魔力——用脚本把工具串起来

### 为什么"组合"很重要？

一个工具能做的事情是有限的。但如果能把多个工具组合起来，能做的事情就多得多了。

> 举个例子。你有三个工具：
> 
> \- **工具 A** ：把 PDF 文件转成文字
> 
> \- **工具 B** ：翻译文字
> 
> \- **工具 C** ：把文字转成语音
> 
>   
> 
> 组合使用：先用 A 把英文 PDF 转成英文文字 → 再用 B 把英文文字翻译成中文 → 最后用 C 把中文转成语音

组合能力，是工具生态的核心价值。

### Command Tools 怎么组合？

Command Tools 天然就能组合，因为命令行有"管道"设计。管道就是把一个命令的输出。在命令行里，用 `|` 符号表示。

比如：

```js
工具A input.pdf | 工具B | 工具C > output.mp3
```

这条命令做了什么？

1.  `工具A input.pdf` ：把 input.pdf 转成文字，输出文字
    
2.  `|` ：把上一步的输出传给下一步
    
3.  `工具B` ：把收到的文字翻译成中文，输出中文
    
4.  `|` ：把上一步的输出传给下一步
    
5.  `工具C` ：把收到的中文转成语音，输出语音
    
6.  `> output.mp3` ：把语音保存到 output.mp3 文件
    

一行命令，就把三个工具串起来了！

### 还能用脚本做更复杂的组合

除了管道，你还可以写脚本（比如 bash 脚本）来组合 Command Tools。脚本可以做更复杂的事情，比如：

```js
#!/bin/bash# 遍历所有 PDF 文件for pdf in *.pdf; do    echo "Processing $pdf..."
    # 转文字    text=$(工具A "$pdf")
    # 如果文字为空，跳过    if [ -z "$text" ]; then        echo "No text found, skipping."        continue    fi
    # 翻译    translated=$(echo "$text" | 工具B)
    # 转语音并保存    echo "$translated" | 工具C > "${pdf%.pdf}.mp3"
    echo "Done: ${pdf%.pdf}.mp3"done
```

这个脚本会自动处理当前文件夹里的所有 PDF 文件，把它们都转成中文语音。 **这就是 Command Tools 的组合能力：用管道快速串联，用脚本做复杂编排。**

## 为什么说 “AI 使用工具的终极形态是 Command Tools，MCP已经可以抛弃， Skill 可以继续和 Command Tools 搭配”

### 三个层次，各有各的用

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

### 决定生态能不能跑起来的，是 Command Tools

为什么这么说？因为生态的本质是“让更多人能用、能贡献、能受益”。

-   **MCP** 让 AI 能连上工具，但工具本身可能很难用、很难装、很难传
    
-   **Skills** 让我们能描述能力，但描述再好，也没法直接跑，也没法直接发给别人
    
      
    

只有 **Command Tools** ：

-   能直接跑（可执行）
    
-   自带说明书（--help、--skill）
    
-   能直接发给别人（可分发）
    
-   能升级、回滚（可版本化）
    
-   能和其他工具串起来（可组合）
    

  


**这才是真正能让生态跑起来的东西。** 此外，你依然可以通过 Skills 的方式来二次定义 Command Tools，实现更加个性化的定制。你的Skills 此时是完全文本化的，是可以直接分发的。MCP么，可以进入垃圾箱了。

## 是理论么？

## InfiniSynapse已经提供了

## Command Tools的实现

## 好了，这篇超级啰嗦的文章终于要结束了，现在就有这样的工具送到你手上：进入 https://www.infinisynapse.cn, 注册登录后，点击【Agent工具市场】就可以免费获得 InfiniSynapse 为大家提供的工具。

### Tools 能做什么？

### 包括但不限于（以 InfiniSynapse 为例）：

为了快速体验一下这些 Tool ，你可以登陆 InfiniSynapse 网页版 app.infinisynapse.cn/tasks ，在工具市场也可以看到你获取的所有工具。

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

-   Office文档实时对话式编辑修改
    
    > 提示词：在sheet年份对比表中，在第一行添加一个醒目的标题，背景色改为蓝色
    

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E) ![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

-   Markdown 格式文件一键生成 PPT/PDF/Word 文档
    

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

-   一句话爬取小红书、百度等任意网站内容
    

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E) ![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

-   用Command Tool minimax\_mage 一句话生成图片
    

> 提示词：帮我生成一个可爱卡通风格的蒙娜丽莎头像

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

你还可以把 Tool 使用的最佳实践放在 Skills 里，实现更多复杂的工作流，提高工作效率和效果。

### 我们送出的 Office 套件，多模态工具

### 所有工具都可以直接给到 MoltBot 使用

我们相信，好的工具就应该实实在在地解决问题。所以，我们首批开放了包含上面展示的 **Office套件桶、多模态工具、预测天气、地图功能** 等17个常用工具，只要注册，就能 **永久免费** 使用。更重要的是，我们秉持开放的理念，这些工具下载后不仅能在 InfiniSynapse 上使用， **也同样兼容 MoltBot（ClawdBot）和其他主流的 Agent 平台，真正做到“一次获取，处处可用”。**

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

我们还在努力打磨更多好用的功能。同时，我们还推出 **99元包月/999元包年** 的订阅套餐， 可以更优惠、更方便的带你体验更多第三代技术～

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

## 附录：名词对照表

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

如果你也面临着复杂的数据分析挑战，欢迎体验~


**地址：** https://www.infinisynapse.cn

Web ： https://app.infinisynapse.cn/tasks

  

现在联系小助手进入天使用户群，能获得免费20RMB额度哦⬇️

![图片](https://mp.weixin.qq.com/s/data:image/svg+xml,%3C%3Fxml%20version='1.0'%20encoding='UTF-8'%3F%3E%3Csvg%20width='1px'%20height='1px'%20viewBox='0%200%201%201'%20version='1.1'%20xmlns='http://www.w3.org/2000/svg'%20xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg%20stroke='none'%20stroke-width='1'%20fill='none'%20fill-rule='evenodd'%20fill-opacity='0'%3E%3Cg%20transform='translate(-249.000000,%20-126.000000)'%20fill='%23FFFFFF'%3E%3Crect%20x='249'%20y='126'%20width='1'%20height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

  

作者提示: 个人观点，仅供参考

继续滑动看下一个

InfiniSynapse

向上滑动看下一个