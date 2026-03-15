# Flow Memory System

Flow Memory System 是一套面向“AI 编程协作”的模板型工具。

它想解决的问题不是“AI 会不会生成代码”，而是：

`AI 在持续开发时，能不能始终搞清楚当前任务状态，以及相关文件、页面、状态、服务之间到底是什么关系。`

[English README](README.md)

## 这个项目到底是干嘛的

很多 AI coding 场景里，真正缺的往往不是“生成能力”，而是：

- 任务状态能不能持续保持一致
- 文件关系能不能持续保持一致
- 改一个共享点时，能不能知道还会影响哪些链路

所以 Flow Memory System 的核心思想不是：

- 按目录组织 AI 的工作记忆

而是：

- 按业务链路组织 AI 的工作记忆

原因很简单：

- 目录是工程师为了存放文件设计的
- 链路才是产品真实运行的方式

我们最终想要的是：

- 能解决问题的智能体

而不是：

- 只会检索文件的助手

## 两层核心结构

Flow Memory System 不是只有“一条链路一张卡”。

它实际上有两层：

### 1. Flow Card

Flow Card 记录一条业务链路的完整信息，比如：

- 从哪个入口进入
- 用户点了哪个按钮
- 跳到了哪个页面
- 调用了哪个服务
- 写入了哪个状态或存储
- 常见失败点是什么

这可以理解成“站点级视角”。

### 2. Metro Map

Metro Map 会把多条链路通过共享页面、共享状态、共享服务、共享持久化连接成一张全局图。

这可以理解成“地铁图视角”。

它的价值在于：

- 你改了一个共享节点，马上能看出会影响哪些 flow
- AI 不用每次都重新扫整个仓库
- 非技术用户也能理解整个产品的运行路线

## 这个仓库提供什么

- 一套可直接运行的 `flows/` 和 `schemas/` 示例数据
- Python 版 YAML 校验、查询和辅助脚本
- 给非技术用户使用的 Tkinter 图形界面
- 把 Flow Card 自动转成“文字版跳转逻辑”的能力
- 给 AI agent 复用的接入提示模板

## 模板结构

```text
flow-memory-system/
  docs/
    USER_GUIDE.md
    STARTER_GUIDE.md
    SCREENSHOTS.md
    screenshots/
  flows/
    cards/
    nodes/
    map.yaml
    conventions.md
  schemas/
    FlowCard.schema.json
    Node.schema.json
    Map.schema.json
  CODEX_ONBOARDING_PROMPT.md
  fm_app.py
  flow_memory.py
  ai_helper.py
  validate.py
```

## 给小白的上手方式

如果你不懂代码，最推荐的使用方法其实很简单：

1. 下载这个项目，并安装依赖
2. 把 [docs/STARTER_GUIDE.md](docs/STARTER_GUIDE.md) 和 [CODEX_ONBOARDING_PROMPT.md](CODEX_ONBOARDING_PROMPT.md) 给你的 Codex 或其他 AI agent 阅读
3. 让 AI 先帮你给自己的项目建立 `flows/` 和 `schemas/`
4. 打开 Flow Memory System 图形界面
5. 点击 `Import Project / 导入项目`
6. 导入你自己的项目目录
7. 通过 `Describe Flow / 文字链路`、`Show Map / 显示地图` 等功能查看项目的真实跳转逻辑
8. 如果发现哪一步不对，再直接用自然语言告诉 AI “问题可能出在这一步”

也就是说，普通用户不需要先看源码，而是先看“业务链路”。

## 快速开始

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

验证示例项目：

```bash
python3 validate.py
```

启动图形界面：

```bash
python3 fm_app.py
```

生成某条流程的文字链路：

```bash
python3 ai_helper.py describe flow.text_record_lifecycle
```

## 文档入口

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md)：面向使用者和 GUI 操作的手册
- [docs/STARTER_GUIDE.md](docs/STARTER_GUIDE.md)：把这套系统接入新项目时的指导
- [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md)：真实截图与界面说明
- [CODEX_ONBOARDING_PROMPT.md](CODEX_ONBOARDING_PROMPT.md)：给 AI agent 的接入提示模板

## 别人那种 Demo 一般是怎么做的

常见有三种方式：

### 1. 本地 Demo

用户下载代码后在自己电脑上运行。

优点：

- 最简单
- 不需要云端部署
- 最适合桌面工具和内部工具

这就是当前仓库的默认方式。

### 2. 可下载应用包 Demo

作者把桌面程序打包成 `.app`、`.exe` 或 `.dmg`，用户下载后直接双击运行。

优点：

- 对小白更友好
- 仍然不一定需要云端运行

### 3. 浏览器在线 Demo

用户打开一个网页链接就能试用。

这种通常就需要云端部署，常见平台有：

- Vercel
- Netlify
- Render
- Railway

如果以后你希望别人“点开链接直接试”，那就需要额外做一层 Web Demo。

## 公开仓库说明

- 本仓库不会提交本地日志、虚拟环境、私有规划文档、本地配置和构建后的 `.app` 包。
- 它更适合作为“模板项目 / starter repo”，而不是直接对外提供 SaaS 服务。
- 如果后续想让别人直接在浏览器里试用，可以在这套数据模型之上再增加一个 Web Demo 层。
