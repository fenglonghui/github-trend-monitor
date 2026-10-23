# GitHub 技术趋势监控器

每周一北京时间/韩国时间需要注意：当前配置为**韩国时间周一 09:00**（UTC 00:00），对应**北京时间周一 08:00**。如希望北京时间周一 09:00，将 cron 改为 `0 1 * * 1`。

## 运行

1. 创建一个新的 GitHub 仓库（推荐 public，例如 `github-trend-monitor`）。
2. 上传本文件夹的所有内容，包括隐藏文件 `.github/workflows/weekly.yml`，保持路径不变。GitHub 网页一次上传时也要确认隐藏目录被保留。
3. 打开仓库 `Settings → Actions → General → Workflow permissions`，选择 `Read and write permissions` 并保存（如组织政策禁止此权限，则需要管理员协助）。
4. 打开 `Actions → GitHub Weekly Trend Monitor → Run workflow` 手动测试。
5. 成功后查看 `LATEST.md` 和 `reports/YYYY-MM-DD.md`；也可在单次 Actions 运行页面下载 Artifacts。

本地测试（Mac）：
```bash
python3 -m pip install -r requirements.txt
python3 scripts/report.py
```

## 数据范围

- GitHub 本周 Trending 总榜、Python 本周榜、TypeScript 本周榜。
- AI Agent、LLM 使用项目名称及简介关键词从采集结果中过滤，因此是**趋势样本**而不是全站完整主题榜。
- Weekly Stars 由 GitHub Trending 网页提供；HTML 若变化可能导致采集失败。
- GitHub 定时任务可能延迟，长期不活跃的公共仓库定时工作流可能被 GitHub 自动停用，需要检查 Actions。
- Actions 的成功运行不等于邮件推送；GitHub 默认通知需用户自行设置。通过仓库中的 LATEST.md 查看周报最可靠。
