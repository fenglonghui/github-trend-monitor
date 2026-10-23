# GitHub Trend Monitor

GitHub 技术趋势自动监控系统

基于 Python、GitHub Trending、GitHub Search API 和 GitHub Actions，自动发现热门开源项目，按技术主题分类，定期生成 Markdown 技术趋势周报。

## 1. 项目目标

建立可持续运行的 GitHub 技术趋势监控机制，帮助开发者、产品经理和技术团队快速发现值得关注的开源技术与工具。

## 2. 监控范围

| 分类 | 主要关注内容 |
|---|---|
| GitHub Trending | 全站每周热门开源项目 |
| AI Agent | 智能体框架、多智能体、自动化工作流 |
| LLM | 大语言模型、模型推理及部署 |
| Python | Python 生态热门开源项目 |
| TypeScript | TypeScript 生态热门开源项目 |
| MCP | MCP Server、MCP Client、模型上下文协议 |
| RAG | 检索增强生成、向量检索、GraphRAG |
| Skills | Agent Skills、SKILL.md、可复用技能包 |

## 3. 核心功能

- 自动采集 GitHub Trending Weekly 榜单。
- 根据主题关键词识别相关开源项目。
- 通过 GitHub Search API 扩展专题项目发现。
- 按分类生成热门项目列表。
- 记录项目 Star 数据与历史快照。
- 自动生成 Markdown 技术周报。
- 使用 GitHub Actions 定时运行。
- 支持手动触发和查看历史报告。

部分功能依赖对应版本的 `report.py` 实现。

## 4. 项目目录

```text
github-trend-monitor/
├── .github/
│   └── workflows/
│       └── weekly.yml
├── config/
│   └── topics.json
├── scripts/
│   └── report.py
├── reports/
├── requirements.txt
├── README.md
└── LATEST.md
```

## 5. 本地运行

### 5.1 获取项目

```bash
git clone https://github.com/fenglonghui/github-trend-monitor.git
cd github-trend-monitor
```

### 5.2 创建 Python 虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 5.3 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 5.4 生成报告

```bash
python scripts/report.py
```

### 5.5 查看报告

```bash
open LATEST.md
```

以上打开命令适用于 macOS。

## 6. GitHub Actions 自动执行

工作流配置文件：

`.github/workflows/weekly.yml`

默认计划为每周一执行一次，也支持从 GitHub Actions 页面手动运行。

操作路径：

GitHub 仓库 → Actions → GitHub Weekly Trend Monitor → Run workflow

生成的报告可以通过仓库文件或 Actions Artifacts 查看。

## 7. 自定义监控主题

使用 `config/topics.json` 管理监控关键词与语言分类。

修改主题配置后，应先在本地运行 `report.py` 测试，再提交到 GitHub。

## 8. Stars 数据说明

系统可能使用两类 Star 数据：

**Trending 本周新增 Stars**

来源于 GitHub Trending 页面显示的周期热度。

**历史快照 Stars 增长**

通过对比项目在不同采集时间的累计 Stars 计算增长值。

注意：

- 两种指标的计算时间窗口可能不同。
- 新发现的项目可能没有历史快照。
- 没有历史基准时，不应把累计 Stars 当作本周新增 Stars。
- GitHub Search API 的 Stars 排序通常表示累计 Stars 排序，而非周增长排序。

## 9. 生成的报告

`LATEST.md`：最新一次技术趋势报告。

`reports/`：历史报告及采集快照（以程序实际输出为准）。

## 10. 已知限制

- GitHub 页面结构变化可能影响 Trending 采集。
- GitHub Search API 存在请求频率限制。
- 基于关键词的主题分类可能出现遗漏或交叉。
- 数据可能存在短暂延迟。
- Trending 榜单与专题发现样本不代表 GitHub 全部仓库的完整排名。

## 11. 后续优化计划

- [ ] 中文项目简介与技术亮点分析
- [ ] MCP、RAG、Skills 专题精细化分类
- [ ] 历史增长趋势图
- [ ] 热门项目去重和异常数据检测
- [ ] 产品应用场景和技术选型分析
- [ ] 邮件或消息通知
- [ ] 可视化趋势 Dashboard

## 12. 技术栈

- Python 3.12
- Requests
- Beautiful Soup
- GitHub Actions
- GitHub Trending
- GitHub REST API

## 13. License

许可证待确定；在选择许可证前，不应假定项目已授权第三方修改和再分发。
