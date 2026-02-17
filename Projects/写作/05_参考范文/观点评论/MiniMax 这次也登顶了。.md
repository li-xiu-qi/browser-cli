---
title: "MiniMax 这次也登顶了。"
source: "https://mp.weixin.qq.com/s/IRdmaNlsadPCr7TutA0OyA"
clipped: 2026-02-16
tags:
  - clippings
---

原创 阿颖 *2026年2月16日 10:35*

这两天，在 AI 行业里的朋友，应该都感觉到了什么叫百花争艳吧。一个模型接着一个模型，而且坦白讲，每一个都已经不差。

我跟不在这行的朋友聊天，经常说一句话：

我们可能得意识到，现在就是 1800 年前后的社会状态。AI 就像当年蒸汽机在英国大地上轰隆作响，只是很多人还没反应过来。

从 GPT 5.3 Codex、Opus 到最近国内的 GLM 5、MiniMax 2.5、Seed 2.0 等一系列模型的发展趋势可以看出来，原生的 Agentic 模型已经是大势所趋。

去年的这时候，DeepSeek R1 的推理模式还让大家兴奋呢，现在就成了 Agentic。

模型的发展速度真是快。

要放假了。我特别想写下 MiniMax M2.5。我说它登顶了可能很多人会觉得标题党，但这确是我内心的真实感受。

我对比了几个任务，不看 Benchmark，不看别人的评价，觉得 M2.5 没有哪里比 Opus 4.6 差。

甚至昨天手忙脚乱，没改 Claude Code 配置，我一度以为 M2.5 就是 Opus 4.6。后来一看，生效的配置文件里还是 MiniMax 的 API Key。

国产模型这两个月的突破还是非常明显。

GLM 5 也发了，我知道很多人会问 MiniMax 2.5 和 GLM 5 的区别，我想说，两者都已经不差。但有各有千秋。

大家不需要看什么 BenchMark，直接上手看看就能感觉到差别。

最近一个月我几乎把各个公司的 Coding Plan 买了一遍，我的感觉是，MiniMax 的模型性价比是最高的。

包括这轮 M2.5 发布后，能明显感觉到， MiniMax 的策略是打又便宜又快又好用的心智 。而且是面向所有的 Coding 场景。

这么多模型里，我刚深度检索了下，MiniMax 是第一个公开宣布或者强调他们在超过 10 种语言的真实环境中进行训练。

当然，我相信，其他公司的训练数据里肯定也有这些语言，只是这些信息能让我们理解 MiniMax 的模型思路，他们要做的是全栈。因为之前很多模型轻后端，重前端。

其实后端的场景非常重要。

这次 MiniMax 还有一个亮点我觉得被低估了：速度。

过去一年只要你认真用 AI 写过代码，一定体会过那种感觉。模型在跑，你干等着，然后有人说趁这个时间可以抽根烟、上个厕所。

听起来好像挺潇洒，但仔细想想，这其实是个问题。

尤其是短任务。你就改个小功能，结果等了好几分钟，去倒杯水回来，代码是写好了，但你得花十分钟重新捡起刚才的思路。

这就是心流的代价。不是 AI 写不好，是它写得太慢，把你的专注力打断了。一旦上下文丢了，重新进入状态的成本比你想象的高得多。

速度直接影响协作体验的核心指标。 这是我的感受。具体数据我不说了，大家可以去查。官方的文章在这里， [有具体的指标](https://mp.weixin.qq.com/s?__biz=MzE5MTA3NzcxMQ==&mid=2247487796&idx=1&sn=414621ef4b131b49b0991cdc2857d198&scene=21#wechat_redirect) 。

除了性价比和速度，M2.5 还有一个变化更值得关注：它演化出了原生的 Spec 行为。

什么意思？简单说，它不再是一个只会埋头写代码的执行者了。它的做事方式彻底变成先结构后细节。

以前的模型是什么样的？你给它一个任务，它上来就开干，直接写代码。能跑吗？大概率能跑。但写出来的东西经常是头痛医头，缺乏整体设计感。

M2.5 不一样。你把任务丢给它，它会先停下来想一想。先拆解功能，先理清模块之间的关系，先把架构搭好，然后再动手。

你看下面的截图，它先创建了 Spec 的文档。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/iagroyM7YaBn10trsklUicV8RIdzVcyBalJqzCA1piaaK0FoUiaAF9crGicESKkBcVmy9nalwXSMZrwUiaa1UMBTP2VhB6q9jUb36TxvEdr2gsKuw/640?wx_fmt=png&from=appmsg#imgIndex=0)

从一个写代码的工具，变成了一个会做系统设计的协作者。原生的 Spec 对于复杂任务，真的特别友好。

我接着给大家看几个真实的 Case，从前端到后端。

******[#01](javascript:;)******

**Case 1：春节红包**

这是一个纯粹的前端项目。我花了 20 分钟时间跑出来的。

这个项目比较简单，但大家看，动画效果还不错。这是我们公司去年刚毕业的，非计算机专业的同学跑出来的。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/iagroyM7YaBmh731K3uky03ibAU9fsoF95bllVODBOy0CNMd0iasBXgvaO9dFaNSrnotzTib3ogz29r2GmX8hR0AYTgtzLxfsC7Ms13QGt0lV2E/640?wx_fmt=png&from=appmsg#imgIndex=1)

******[#02](javascript:;)******

**Case 2：前后端兼具的作文 Review 产品**

同样，把提示词扔给 Claude Code 后，M2.5 会先创建 SPEC.MD。这是刚才提到过的优点。原生的 Agent 模型就是这个意思。

即便没有 Claude Code 的脚手架，它同样会这么思考。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/iagroyM7YaBmyregQj1btqDRpDsAicusZT3soiaJBaeCxWLbOW350Fxb6mRBcUV4SrIUdxUplGLJHHicZHrSERXqYG08n07a9Jia7CEmdELL98Tg/640?wx_fmt=png&from=appmsg#imgIndex=2)

这是项目的结构。后端是 Go 语言，我没让他把数据放到 MySQL，而是放到了 Notion 的数据库。

最近我很喜欢 Notion 的数据库，感觉日常很多数据，可以直接放 Notion，这样查看起来会更方便。

![图片](https://mmbiz.qpic.cn/mmbiz_png/iagroyM7YaBlhmHoeeRp8Uc5gbtdohqSibhpaBbyoUXaYyBR3GiaN9DJryUc0A56jvmseUEjVFS4dQ9QIHQ7b8Xwia72sV5pBtu5zYOuicQXDnKk/640?wx_fmt=png&from=appmsg#imgIndex=3)

下面这是主页。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/iagroyM7YaBnFbsJxBrgTL5PGwLQ9178n1qDvSu7kx9lcJZc0sctDwYD67xH78q8b15DD17UVg7qvn5gxfhBKDVuHc1Za1lDbQDib601T5fa4/640?wx_fmt=png&from=appmsg#imgIndex=4)

UI 还是挺好看的。上传完图片后，会用 OCR 转为文字。然后再请 AI 给孩子一个反馈。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/iagroyM7YaBmD5eNjjd4icjLwRmap4aY3t6GoBibtwurUhSZicTrG8PDXZXLTKgLX2uHud5U1Lr4jg1CWxS45roAQiciaBibgFL0sttLL6S8v8IkGY/640?wx_fmt=png&from=appmsg#imgIndex=5)

这是后端的一些代码逻辑：

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/iagroyM7YaBlr0EntB2wd6Wmp6XeNqpfJSI3Qj9icr7FllQ5weGvK8JLcJgraj4jD3nF8xOzcdibatBjRUxfu2mZDyQmsE6IeCFjLnZZLSjQzo/640?wx_fmt=png&from=appmsg#imgIndex=6)

我给大家录屏跑一次整体的效果。从上传图片，到 AI 给评语，再到浏览所有的作文，并朗读，最后存到 Notion 当中。

这个流程我做了 2 个多小时，跑通了。特别有成就感。

******[#03](javascript:;)******

**Case 3：后端高并发场景**

这是我让 M2.5 给我写的一个秒杀的后端服务项目。同样是在 Claude Code 里。

我非常惊讶，它可以考虑到 Redis、限流器、分布式锁、消息队列这些层面的问题。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/iagroyM7YaBncZ4LxpH2hPeCxzGCFkMOJq12dKSQrKZ3ZAHibmLQDFTwPUUuWlwpEoHhvckQbCbObTPdOauRLEYBcadumRQJSBsH8JhTIRV2Q/640?wx_fmt=png&from=appmsg#imgIndex=7)

大家可以看看代码结构，我导入到了 Trae 中。

![图片](https://mmbiz.qpic.cn/mmbiz_png/iagroyM7YaBm0FVbd7FxqjceLuheFbA6aQbZ8eaR74of6B3iaKaJQBrGiaiaiaKC2w4y5Cghia4b1uJiatNSsIsou25QABlrlgPG9DPa35SdPsw2hY/640?wx_fmt=png&from=appmsg#imgIndex=8)

我逐一看了下这些代码，它考虑到了下面这些问题。虽然有些地方和我预期的不一样，但整体看，绝对算得上一个高级工程师的水准了。

1） 库存扣减、用户购买检查、加锁解锁都使用 Lua 脚本保证原子性，避免了分布式环境下的竞态条件

2）使用 Redis 实现分布式锁，防止并发竞争，设置过期时间，避免死锁

3）滑动窗口限流，防止单个用户恶意刷单，保护系统不被突发流量打垮

4）使用 Redis List 作为消息队列，10 个线程池消费者异步处理订单，削峰填谷

5）库存、用户订单记录都存在 Redis 中，避免直接访问数据库

上面聊的更多是 M2.5 好的地方。毕竟测模型嘛，大家更关注的还是它能干什么。但公平起见，我也有必要把使用过程中遇到的一些问题说出来。

第一，部分场景下，程序员思维还是偏弱。

比如孩子作文那个项目，保存到 Notion 的功能一直报错。我反复让它修，它每次都说修好了，但我一测还是有问题。

来回几轮之后，我直接跟它说：你写个单元测试，或者加点 log，先看看到底哪里出了问题。

给到这一步更明确的指令之后，它才最终定位到了根因。也就是说，遇到不好排查的 bug 时，它还不太会主动换思路去调试，需要你推一把。

第二，执行任务过程中的外部检索，有时候会乱。

比如前面提到的 TTS 部分，我本来想接入字节的 TTS 服务，我认为它应该可以自己找到正确的接入方式。

但似乎没有，写出来的代码跑不通。后来我自己去官方文档把示例代码拿回来发给它，它才完成了接入。

这个我原本觉得模型应该能自己搞定，但实际上没有。

第三，我还测试了它对 Anthropic Skill 的理解。

Skill 是什么、有什么用，它完全清楚，也能帮我改里面的代码。

但有一个场景让我觉得还差点意思：我让它调整完 Skill 里的代码之后，顺便把对应的 Skill MD 说明文档也同步更新一下，这一步它没做好。一直无法理解我的意图。

类似这样的地方，肯定还有欠缺。大家使用过程中就会知道。但整体我觉得还是很不错的。

******[#04](javascript:;)******

**写在最后**

写这篇文章的时候，我一度很纠结。因为我觉得 M2.5 最出色的能力其实在后端，Java、Go、Rust 这些语言。

但后端不像前端，没法截个图就让你直观感受到它的厉害。案例不好呈现，这事确实让人头疼。

除了前面提到的性价比，我觉得 M2.5 这次的方向也非常明确：全栈编程 + Office 生产力。

这其实跟 Opus 4.6 的路线如出一辙。Opus 4.6 这次除了 Coding 能力提升之外，也在慢慢向更多生产力场景延伸。M2.5 走的是同一条路。

我自己同时也在买 Anthropic 的 API。因为实际使用中你会遇到这种情况：某个模型跑不出来，那就换一个试试。

但就目前而言，我们团队的主力模型已经切到 M2.5 了。大概 95% 的场景，我们觉得它都能搞定。剩下那 5%，换个模型再试试。再不行，那就只能自己上手了。

就这样。

除夕了。这是昨天提前写好的文章。本来今天想休息，但晚上在社群里和几个朋友聊 High 了，我觉得应该写写这次的 M2.5。  

另外，昨天晚上我看到他们公众号说，最新上线了 MiniMax-M2.5-highspeed，支持 100 TPS 极速推理，三档的 Coding Plan 都可以用。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_jpg/iagroyM7YaBn2mjvrje6gPAxrdwvTiccJFuqQKA3wA8YcvDE3E3QP4R9ckOkImcqfjbeK8X8dJC9ibNWaWlqxLWUkbibCkEX1ATZEqZNqMPYY34/640?wx_fmt=jpeg&from=appmsg#imgIndex=9)

这一年，我也是经常写文章，虽然我没有能力去研发模型，但我觉得，能用另外一种方式，参与大模型浪潮，也是与有荣焉了。

马年加油。

继续滑动看下一个

AI产品阿颖

向上滑动看下一个