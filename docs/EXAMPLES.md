# Examples · 当前可运行示例

以下命令均基于 v0.2.1，可在仓库根目录执行。

## 安装

```bash
pip install -e .
```

## 生成六类内容

```bash
python -m htmlninefox expert "做一个 SaaS 落地页，品牌狐构" --type landing --quiet-llm -o ./output
python -m htmlninefox expert "做一个运营数据看板" --type dashboard --template shadcn-dashboard --quiet-llm -o ./output
python -m htmlninefox expert "做一个 AI 产品发布会 PPT" --type deck --quiet-llm -o ./output
python -m htmlninefox expert "做一张活动海报" --type poster --quiet-llm -o ./output
python -m htmlninefox expert "写一份产品方案文档" --type doc --quiet-llm -o ./output
python -m htmlninefox expert "写一份系统架构文档" --type archdoc --quiet-llm -o ./output
```

## 反馈迭代

```bash
python -m htmlninefox feedback --project ./output/html9n-<时间戳> --note "颜色再深一点，标题大一点"
```

## Web / PWA 工作台

```bash
python -m htmlninefox serve --port 8620
```

浏览器打开 `http://127.0.0.1:8620`。Windows/macOS 可点击“安装”；iPhone/iPad 需要将服务部署到 HTTPS 后再“添加到主屏幕”。

仓库内还提供：

- `examples/expert_landing.sh`
- `examples/expert_dashboard.sh`
- `examples/feedback_iteration.sh`
- `examples/feedback_python.py`
