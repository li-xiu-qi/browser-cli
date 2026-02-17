---
title: "Agent开发的下一个阶段：从工作流编排到Skill编排"
source: "https://mp.weixin.qq.com/s/fGu5azU7yaTIXB83dqnK8w"
clipped: 2026-02-16
tags:
  - clippings
---

![cover_image](https://mmbiz.qpic.cn/sz_mmbiz_jpg/iacaCWlP1x1zrwNl2Wnnbw7GPpreBBRu16QHPicK3yg6jJNg7WCXoOK4diaJnuwq97Bf8n32cWGRmltIuPicQCJ1nibJhbiaGeeOpdibG8wPn3V1lQ/0?wx_fmt=jpeg)

原创 字节笔记本 [字节笔记本](javascript:void\(0\);) *2026年2月16日 11:59*

Agent 开发的下一个风口就是从单一 Skill 的开发，进化到 Skill 的编排。

关注我比较久的朋友都知道，我们之前写过很多 Skill。

比如内容发布 Skill，它可以帮我们将写好的内容直接发布到小红书。 [这套Skill技能包让我的小红书粉丝直接破千！](https://mp.weixin.qq.com/s?__biz=MzIzMzQyMzUzNw==&mid=2247512269&idx=1&sn=d116d8273c379367b42847ee4f78e5e7&payreadticket=HLdXey30Be5hg69iO5jyU_FDBCBYbBWyR-ZJp-V9SL5qNhaQJUDoeqcqoD_cd0FJReIVDQI&scene=21#wechat_redirect)

又比如生成漫画，专门用来生成一致性的漫画风格图片。 [使用Claude Code Skill 实现爆火的Nano漫画风格学习读本工作流](https://mp.weixin.qq.com/s?__biz=MzIzMzQyMzUzNw==&mid=2247509044&idx=1&sn=14e976c6de43fa759f4f6b4576f545b4&payreadticket=HI5xd57BY1F2rGa5MPy8UR3jSzXvYyctYdSPCpUhUgbZ7dHt-Nc-riYMIF8d1M8YVLe_w0Y&scene=21#wechat_redirect)

虽然这些 Skill 内部组合了各种要素，表现得像一个微型应用，但它们本质上是静态且独立的。

我之前还尝试过在 Obsidian 里通过组合这些 Skill，构建了一个工作流。 [神仙组合！Claude Agent Skills +Obsidian的个人数字资产管理](https://mp.weixin.qq.com/s?__biz=MzIzMzQyMzUzNw==&mid=2247512534&idx=1&sn=4f5897e26bd605db992cbb8797509edc&scene=21#wechat_redirect)

但是在制作和组合的过程当中，会发现编排的过程非常的复杂，而且极难的调试。

现在终于等到了Skill终于进化到新的阶段， Compose。

它不再让你去纠结单个 Skill 怎么写，而是让你站在更高的维度，去指挥多个 Skill 进行组合式作战。

Skill Compose完美继承了 OpenClaw 的核心思想， [抽掉龙虾的筋！还原OpenClaw的核心，实现人人可定制的Agent](https://mp.weixin.qq.com/s?__biz=MzIzMzQyMzUzNw==&mid=2247513664&idx=1&sn=6bce385e0202cc29b590bd1658f8255f&payreadticket=HDkp07x3urPl0JRJxGFKxsdS8Ejvz61iQCla2SXKP8hTXLo-y17QAb7w9KNM0lBxQwrwwM0&scene=21#wechat_redirect) 将之前的 Skill 进行不断的优化组合，甚至让系统自主发现需要的 Skill。

在 Skill Compose 的逻辑里，Skill 将下沉为更原子化的单元。

以前我们写一个 写作助手 Skill，可能要把 搜索、阅读、大纲、正文 生成全塞在一个包里。

现在不同了，搜就是搜，读就是读， 这种原子化的好处在于极致的复用性。

当你需要一个 行业分析 Agent 时，系统会自动调用 搜索 Skill 和 阅读 Skill 。

当你需要一个 爆款文案 Agent 时，系统会再次调用 阅读 Skill，但这次配合的是 仿写 Skill。

通过这种自由编排，Skill 的使用效果和智能程度都会呈指数级上升，让整个的AI工作流的编排变得更加的灵活，就像搭积木一样简单。

你只管描述，系统负责实现。

你不需要自己去思考第一步做什么、第二步接什么工具。

你只需要用自然语言描述你的意图，Skill Compose 会自动从你的技能库里寻找匹配的原子化 Skill。

如果找不到现成的，它甚至会为你草拟缺失的技能，然后把它们编排成一个完整的 Agent。

这里有两个非常典型的案例：

案例一：从文章到幻灯片

比如你想做一个 从文章到 PPT 的助手。你告诉它需求，它会自动拆解任务。

![article-to-slides-agent.gif](https://mmbiz.qpic.cn/sz_mmbiz_gif/iacaCWlP1x1wC2ZXZIlj9hZKVNdvSpOiaFQ6WZMPoPbrSo3gCnZOAhpFu3qSzNviakuC7IErB3kC8BX7n0prD87L95jUI4o8740PEYicQlzC51M/640?from=appmsg&wx_fmt=gif#imgIndex=0)

它会先调用 阅读 Skill 解析内容，然后调用 提炼 Skill 抽取观点，接着使用 分镜 Skill 生成画面描述，最后输出幻灯片。这在以前需要手动串联四个复杂的步骤，现在系统自动帮你完成了编排。

案例二：化学研究助手 ChemScout

这是一个更牛逼的场景。这个 Agent 需要在隔离的环境中运行，搜索化合物数据库，分析分子结构，并总结报告。

![chemscout-agent.gif](https://mmbiz.qpic.cn/mmbiz_gif/iacaCWlP1x1zSVHibzoic4BhOK70vNWBeCTjLRibnsWOzza7zgSO0UjH1ywAXPBSEkbLJ5xgibDqmGBibgIh9kbzkvBTnI3lkvV5AyfmRHVTca8Gs/640?from=appmsg&wx_fmt=gif#imgIndex=1)

Skill Compose 引入了容器优先的隔离机制。每一个 Agent 都可以运行在独立的 Docker 容器里。

你可以放心大胆地让 AI 去执行 Python 代码，去跑数据分析，而不用担心搞挂你的本地环境。

开始编排

Skill Compose 的部署非常简单，完全基于 Docker，不依赖复杂的本地环境配置。

第一步，克隆项目：

```
git clone https://www.google.com/search?q=https://github.com/MooseGoose0701/skill-compose.git
cd skill-compose/docker
```

第二步，配置环境。默认使用 Kimi 2.5 模型，你需要填入 API Key：

```
cp .env.example .env
docker compose up -d
```

第三步，打开浏览器访问 http://localhost:62600，点击 Skill-Compose My Agent。

![a75187bc-94ba-4a42-bdc1-7b46ccec2960.png](https://mmbiz.qpic.cn/sz_mmbiz_png/iacaCWlP1x1wnLniamWnsadFKp0ug3X96VOb6l8bvNjGyaibcKGsIquQm4nTePJqRhzAfTwZfFP2N3jFsFIkooCvZRMNUQHJyNl2X6l9mySof8/640?wx_fmt=png&watermark=1#imgIndex=2)

整个过程没有复杂的连线，没有让人头大的节点配置。唯一要做的就是定义目标，审查系统生成的方案，然后点击运行。

如果只是认为它是单纯的编排，就在低估Compose了。

一个好的 Agent 不应该是写死不动的。Skill Compose 支持从执行轨迹和用户反馈中改进技能。

当发现某个 Skill 在特定场景下表现不好，你可以给出反馈，系统会根据实际运行的效果，提出重写建议。你只需要像代码 Review 一样，审查这些变更，点击接受，你的 Skill 资产就升级了。

这大概是未来的 AI 工作流模样：原子化的 Skill，智能化的编排，以及自我进化的能力。

现在，我们不需要再造更多的轮子，而是要学会如何把现有的轮子，组装成一辆跑车。

告别繁琐的连线，欢迎来到 Skill 编排的时代。

[将1Panel 这样的“大型”应用系统制作成Skill](https://mp.weixin.qq.com/s?__biz=MzIzMzQyMzUzNw==&mid=2247513632&idx=1&sn=7fa51e36b991525b2bf6e0c816fcfe7c&payreadticket=HK8CuWKbBx2xDY9HKCsd4TWxfwthHWeBoNBx9FBXey5ojLTRZ1_aErM_oppDeO0Tdq53BBk&scene=21#wechat_redirect)  

[抽掉龙虾的筋！还原OpenClaw的核心，实现人人可定制的Agent](https://mp.weixin.qq.com/s?__biz=MzIzMzQyMzUzNw==&mid=2247513664&idx=1&sn=6bce385e0202cc29b590bd1658f8255f&payreadticket=HEoJKjt6D0C6CHyQZlCvNMoo7YrJmyrB3YxOqsmvgPY-jUvdlolhgdYmrxDJJJcvgZlZicY&scene=21#wechat_redirect)  

[新上架了一个剪切板APP！分享我的AI开发工作流](https://mp.weixin.qq.com/s?__biz=MzIzMzQyMzUzNw==&mid=2247513650&idx=1&sn=763b6253997a581c4fa6782b1f09fcc0&scene=21#wechat_redirect)  

[为了更爽的Vibe Coding ，我最近又写了几个好用的工具！](https://mp.weixin.qq.com/s?__biz=MzIzMzQyMzUzNw==&mid=2247513617&idx=1&sn=bbeb5a01926a02489e7691ab51c07634&scene=21#wechat_redirect)

继续滑动看下一个

![图片](http://mmbiz.qpic.cn/mmbiz_png/4HWyricuhgQcXaLyxUyPhJLZKEQG5tGdBNkd3q9bets8RaAo1ewHeBiaNf3Y7DKxLhF3jGgDCCjiayicn90DEpzO4Q/0?wx_fmt=png)

字节笔记本

向上滑动看下一个

![图片](https://mmbiz.qpic.cn/mmbiz_png/4HWyricuhgQcXaLyxUyPhJLZKEQG5tGdBNkd3q9bets8RaAo1ewHeBiaNf3Y7DKxLhF3jGgDCCjiayicn90DEpzO4Q/300?wx_fmt=png&wxfrom=18)

字节笔记本