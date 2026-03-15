# Flow Memory System

Flow Memory System 是一套“模板型”工具，用来把项目按照业务流程而不是单纯按照文件夹来理解。它的目标是让开发者、产品人员、测试人员以及 AI 编程助手都能基于同一套结构化信息协作。

[English README](README.md)

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

## 这个仓库提供什么

- 一套可直接运行的 `flows/` 和 `schemas/` 示例数据
- Python 版 YAML 校验、查询和辅助脚本
- 给非技术用户使用的 Tkinter 图形界面
- 把 Flow Card 自动转成“文字版跳转逻辑”的能力
- 给 AI agent 复用的接入提示模板

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

## 公开仓库说明

- 本仓库不会提交本地日志、虚拟环境、私有规划文档、本地配置和构建后的 `.app` 包。
- 它更适合作为“模板项目 / starter repo”，而不是直接对外提供 SaaS 服务。
- 如果后续想让别人直接在浏览器里试用，可以在这套数据模型之上再增加一个 Web Demo 层。
