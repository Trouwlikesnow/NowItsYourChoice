# NowItsYourChoice 阶段 1 实施计划

**项目名**：NowItsYourChoice（缩写 NIYC）


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 MVP——通过飞书 Bot 输入股票代码，结合多周期技术指标、板块新闻、交易纪律，由 LLM 给出操作建议。

**Architecture:** AkShare 抓数据 → GitHub Actions 定时跑 Python 脚本 → 写入飞书 Bitable。飞书 Bot 接收用户消息 → 调用 Dify Cloud 工作流 → 工作流读 Bitable + Dify Knowledge → 调用 DeepSeek-V3 → 返回决策结果。

**Tech Stack:**
- Python 3.11 + AkShare + pandas_ta + requests
- GitHub Actions（定时调度）
- 飞书 Bitable（数据存储）+ 飞书 Bot（交互入口）
- Dify Cloud（工作流编排 + Knowledge RAG）
- DeepSeek-V3（推理模型）

**对应规范文档：** `docs/superpowers/specs/2026-05-07-now-its-your-choice-phase1-design.md`

---

## 里程碑总览

**里程碑 1：数据管道**（Task 0-8） — 完成后每日 15:30 自动抓数据写 Bitable，可独立验收
**里程碑 2：决策引擎与 Bot**（Task 9-13） — 完成后用户可在飞书 Bot 提问获得建议

每个里程碑结束都有一次端到端 smoke test。

---

## Task 0：仓库初始化

**Files:**
- Create: `NowItsYourChoice/.gitignore`
- Create: `NowItsYourChoice/requirements.txt`
- Create: `NowItsYourChoice/README.md`
- Create: `NowItsYourChoice/pyproject.toml`

- [ ] **Step 1：在 GitHub 创建 Private 仓库 `NowItsYourChoice`**

操作：登录 GitHub，新建仓库，勾选 Private，不勾选自动生成 README。

- [ ] **Step 2：本地初始化**

```bash
cd ~/NIYC
git clone git@github.com:<your-username>/NowItsYourChoice.git
cd NowItsYourChoice
```

- [ ] **Step 3：创建 `.gitignore`**

```
__pycache__/
*.pyc
.env
.venv/
venv/
.pytest_cache/
.coverage
htmlcov/
*.log
.DS_Store
.idea/
.vscode/
```

- [ ] **Step 4：创建 `requirements.txt`**

```
akshare==1.14.50
pandas==2.2.2
pandas-ta==0.3.14b0
requests==2.32.3
python-dotenv==1.0.1
pyyaml==6.0.1
pytest==8.3.2
pytest-mock==3.14.0
```

- [ ] **Step 5：创建 `pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "-v"
```

- [ ] **Step 6：创建 `README.md`（占位，记录项目入口）**

```markdown
# NowItsYourChoice

Personal investment management MVP — 决策引擎、关注板块、知识库一体化。
See `docs/superpowers/specs/2026-05-07-now-its-your-choice-phase1-design.md` for design.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
python -m scripts.main
```
```

- [ ] **Step 7：建本地虚拟环境并安装依赖**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 8：提交**

```bash
git add .
git commit -m "chore: initialize project skeleton"
git push -u origin main
```

---

## Task 1：飞书 Bitable 工作区与自建应用配置（手工 + 检查清单）

**说明：** 这一步是飞书后台的图形化配置，没有代码。完成后记录三个关键凭证。

- [ ] **Step 1：创建飞书自建应用**

操作：访问 https://open.feishu.cn → 开发者后台 → 创建企业自建应用 → 名称"NowItsYourChoice"。

记录：`app_id`、`app_secret`。

- [ ] **Step 2：开通应用权限**

在应用 → 权限管理，添加：
- 多维表格：查看、编辑应用所有数据 (`bitable:app`)
- 机器人：发送消息 (`im:message`)、接收消息事件 (`im:message:receive_v1`)
- 联系人：通讯录基础信息（用于消息推送）

- [ ] **Step 3：创建多维表格"NowItsYourChoice"**

操作：飞书工作台 → 多维表格 → 新建。
记录：`base_app_token`（在表格 URL 中，形如 `bascn...`）。

- [ ] **Step 4：在表格内创建 7 张数据表，按规范文档 4.1 节字段建表**

表名清单：
- `板块表`
- `标的表`
- `指标表`
- `行情快照表`
- `板块新闻表`
- `决策记录表`
- `交易纪律表`

每张表字段对照规范文档第 4.1 节逐一建好。**关键约定：**
- 复合主键字段（如指标表的"复合主键"）设为"文本类型 + 主键"
- "周期"、"指标名"等枚举字段用"单选"，提前预填所有备选值（日/周/月；MA5/MA10/MA20/MA60/MACD-DIF/MACD-DEA/MACD-HIST/RSI14/KDJ-K/KDJ-D/KDJ-J/BOLL-UPPER/BOLL-MID/BOLL-LOWER）
- 关联字段（标的表的"所属板块"、新闻表的"板块名"）使用"双向关联"

记录：每张表的 `table_id`。可用 [飞书开放平台 API 调试工具](https://open.feishu.cn/api-explorer) 调用 `GET /bitable/v1/apps/:app_token/tables` 一次性拿全。

- [ ] **Step 5：把应用添加到多维表格的协作者**

打开多维表格 → 右上角分享 → 添加应用 → 选刚才的应用 → 设置为"可编辑"。

- [ ] **Step 6：建立默认视图（看板）**

每张表新建以下视图（按规范文档 5.2 节）：
- 标的表：`关注标的`（按板块分组，按当日涨跌幅倒序）
- 板块表：`板块概览`
- 板块新闻表：`今日新闻`（按发布时间倒序）
- 决策记录表：`决策历史`（按决策时间倒序）
- 行情快照表：`走势图`（按代码筛选，画线图组件）

- [ ] **Step 7：本地建凭证文件 `.env`（不提交）**

```bash
cat > .env <<'EOF'
FEISHU_APP_ID=cli_xxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxx
FEISHU_BASE_APP_TOKEN=bascnxxxxxxxx
TABLE_ID_SECTORS=tblxxx
TABLE_ID_TICKERS=tblxxx
TABLE_ID_INDICATORS=tblxxx
TABLE_ID_PRICE_SNAPSHOTS=tblxxx
TABLE_ID_SECTOR_NEWS=tblxxx
TABLE_ID_DECISIONS=tblxxx
TABLE_ID_TRADING_RULES=tblxxx
EOF
```

- [ ] **Step 8：手工填入初始板块和标的数据**

- 板块表：填入规范文档 6.1 节的 10 个板块
- 标的表：填入 30-50 只关注标的（用户提供）
- 交易纪律表：填入用户提供的初始 10-20 条纪律

- [ ] **Step 9：提交（仅文档变更）**

```bash
echo "记录 Bitable 配置完成，凭证已保存到本地 .env" > docs/setup-log.md
git add docs/setup-log.md
git commit -m "docs: record Bitable workspace setup completion"
git push
```

---

## Task 2：Bitable API 客户端（Python）

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/bitable_client.py`
- Create: `tests/__init__.py`
- Create: `tests/test_bitable_client.py`

封装最小可用的飞书 Bitable HTTP API 调用，包括 token 获取、查询、批量写、批量删。

- [ ] **Step 1：写失败的测试 — token 获取**

`tests/test_bitable_client.py`：

```python
from unittest.mock import patch, MagicMock
from scripts.bitable_client import BitableClient


def test_get_tenant_access_token_returns_token():
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "code": 0,
        "tenant_access_token": "t-fake-token",
        "expire": 7200,
    }
    fake_response.raise_for_status = MagicMock()

    with patch("scripts.bitable_client.requests.post", return_value=fake_response):
        client = BitableClient(app_id="id", app_secret="secret", base_app_token="bt")
        token = client._get_tenant_access_token()

    assert token == "t-fake-token"
```

- [ ] **Step 2：运行测试，确认失败**

```bash
pytest tests/test_bitable_client.py -v
```

预期：`ModuleNotFoundError` 或 `AttributeError`。

- [ ] **Step 3：实现 `BitableClient` 最小代码使第一个测试通过**

`scripts/bitable_client.py`：

```python
import time
import requests


class BitableClient:
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str, base_app_token: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_app_token = base_app_token
        self._token = None
        self._token_expires_at = 0

    def _get_tenant_access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = requests.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu token error: {data}")
        self._token = data["tenant_access_token"]
        self._token_expires_at = time.time() + data["expire"]
        return self._token
```

- [ ] **Step 4：运行测试通过**

```bash
pytest tests/test_bitable_client.py -v
```

预期：1 passed。

- [ ] **Step 5：写失败的测试 — 列表查询**

追加到 `tests/test_bitable_client.py`：

```python
def test_list_records_returns_items_across_pages():
    page1 = MagicMock()
    page1.json.return_value = {
        "code": 0,
        "data": {
            "items": [{"record_id": "r1", "fields": {"代码": "002594"}}],
            "has_more": True,
            "page_token": "tok1",
        },
    }
    page1.raise_for_status = MagicMock()
    page2 = MagicMock()
    page2.json.return_value = {
        "code": 0,
        "data": {
            "items": [{"record_id": "r2", "fields": {"代码": "300750"}}],
            "has_more": False,
        },
    }
    page2.raise_for_status = MagicMock()

    with patch("scripts.bitable_client.requests.get", side_effect=[page1, page2]):
        with patch.object(BitableClient, "_get_tenant_access_token", return_value="t"):
            client = BitableClient("id", "secret", "bt")
            records = client.list_records("tblXXX")

    assert len(records) == 2
    assert records[0]["fields"]["代码"] == "002594"
    assert records[1]["fields"]["代码"] == "300750"
```

- [ ] **Step 6：运行测试，确认失败**

```bash
pytest tests/test_bitable_client.py -v
```

- [ ] **Step 7：实现 `list_records`**

追加到 `scripts/bitable_client.py`：

```python
    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_tenant_access_token()}"}

    def list_records(self, table_id: str, page_size: int = 500, filter_: str | None = None) -> list[dict]:
        url = f"{self.BASE_URL}/bitable/v1/apps/{self.base_app_token}/tables/{table_id}/records"
        page_token = None
        out = []
        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            if filter_:
                params["filter"] = filter_
            resp = requests.get(url, headers=self._auth_headers(), params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Feishu list error: {data}")
            d = data["data"]
            out.extend(d.get("items", []))
            if not d.get("has_more"):
                break
            page_token = d.get("page_token")
        return out
```

- [ ] **Step 8：运行测试通过**

```bash
pytest tests/test_bitable_client.py -v
```

- [ ] **Step 9：写失败测试 — 批量创建**

```python
def test_batch_create_chunks_and_calls_api():
    fake_resp = MagicMock()
    fake_resp.json.return_value = {"code": 0, "data": {"records": []}}
    fake_resp.raise_for_status = MagicMock()

    with patch("scripts.bitable_client.requests.post", return_value=fake_resp) as mock_post:
        with patch.object(BitableClient, "_get_tenant_access_token", return_value="t"):
            client = BitableClient("id", "secret", "bt")
            records = [{"代码": f"{i:06d}"} for i in range(1200)]
            client.batch_create("tbl", records)

    # 1200 条按 500 切片，应调 3 次
    assert mock_post.call_count == 3
```

- [ ] **Step 10：实现 `batch_create`**

```python
    def batch_create(self, table_id: str, records: list[dict], chunk_size: int = 500) -> None:
        url = f"{self.BASE_URL}/bitable/v1/apps/{self.base_app_token}/tables/{table_id}/records/batch_create"
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            payload = {"records": [{"fields": r} for r in chunk]}
            resp = requests.post(url, headers=self._auth_headers(), json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Feishu batch_create error: {data}")
```

- [ ] **Step 11：运行测试**

```bash
pytest tests/test_bitable_client.py -v
```

- [ ] **Step 12：写失败测试 — 批量删除**

```python
def test_batch_delete_chunks_record_ids():
    fake_resp = MagicMock()
    fake_resp.json.return_value = {"code": 0}
    fake_resp.raise_for_status = MagicMock()

    with patch("scripts.bitable_client.requests.post", return_value=fake_resp) as mock_post:
        with patch.object(BitableClient, "_get_tenant_access_token", return_value="t"):
            client = BitableClient("id", "secret", "bt")
            ids = [f"rec{i}" for i in range(1100)]
            client.batch_delete("tbl", ids)

    assert mock_post.call_count == 3  # 500 + 500 + 100
```

- [ ] **Step 13：实现 `batch_delete`**

```python
    def batch_delete(self, table_id: str, record_ids: list[str], chunk_size: int = 500) -> None:
        url = f"{self.BASE_URL}/bitable/v1/apps/{self.base_app_token}/tables/{table_id}/records/batch_delete"
        for i in range(0, len(record_ids), chunk_size):
            chunk = record_ids[i:i + chunk_size]
            resp = requests.post(url, headers=self._auth_headers(), json={"records": chunk}, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Feishu batch_delete error: {data}")
```

- [ ] **Step 14：跑全部测试通过**

```bash
pytest -v
```

- [ ] **Step 15：用真实凭证做一次连通验证**

`scripts/_smoke_bitable.py`（临时脚本，验证后删除或保留）：

```python
import os
from dotenv import load_dotenv
from scripts.bitable_client import BitableClient

load_dotenv()
client = BitableClient(
    os.environ["FEISHU_APP_ID"],
    os.environ["FEISHU_APP_SECRET"],
    os.environ["FEISHU_BASE_APP_TOKEN"],
)
recs = client.list_records(os.environ["TABLE_ID_SECTORS"])
print(f"Got {len(recs)} sectors")
for r in recs[:3]:
    print(r)
```

```bash
python -m scripts._smoke_bitable
```

预期：打印出在 Task 1 Step 8 填进的板块。

- [ ] **Step 16：提交**

```bash
git add scripts/__init__.py scripts/bitable_client.py tests/
git commit -m "feat: add Bitable API client with TDD"
git push
```

---

## Task 3：配置加载

**Files:**
- Create: `scripts/config.py`
- Create: `tests/test_config.py`

集中管理：环境变量、指标列表、周期、滚动窗口天数等。

- [ ] **Step 1：写失败测试**

```python
import os
from scripts.config import load_config


def test_load_config_reads_env(monkeypatch):
    monkeypatch.setenv("FEISHU_APP_ID", "id1")
    monkeypatch.setenv("FEISHU_APP_SECRET", "s1")
    monkeypatch.setenv("FEISHU_BASE_APP_TOKEN", "bt1")
    monkeypatch.setenv("TABLE_ID_SECTORS", "t1")
    monkeypatch.setenv("TABLE_ID_TICKERS", "t2")
    monkeypatch.setenv("TABLE_ID_INDICATORS", "t3")
    monkeypatch.setenv("TABLE_ID_PRICE_SNAPSHOTS", "t4")
    monkeypatch.setenv("TABLE_ID_SECTOR_NEWS", "t5")
    monkeypatch.setenv("TABLE_ID_DECISIONS", "t6")
    monkeypatch.setenv("TABLE_ID_TRADING_RULES", "t7")

    cfg = load_config()
    assert cfg.feishu_app_id == "id1"
    assert cfg.tables.indicators == "t3"
    assert "MA20" in cfg.indicators_by_period["日"]
```

- [ ] **Step 2：实现 `config.py`**

```python
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class TableIds:
    sectors: str
    tickers: str
    indicators: str
    price_snapshots: str
    sector_news: str
    decisions: str
    trading_rules: str


@dataclass
class Config:
    feishu_app_id: str
    feishu_app_secret: str
    feishu_base_app_token: str
    tables: TableIds
    indicators_by_period: dict[str, list[str]] = field(default_factory=lambda: {
        "日": ["MA5", "MA10", "MA20", "MA60", "MACD", "RSI14", "KDJ", "BOLL"],
        "周": ["MA4", "MA13", "MA26", "MACD", "RSI14"],
        "月": ["MA6", "MA12", "MACD"],
    })
    snapshot_window_days: int = 90
    news_window_days: int = 60


def load_config() -> Config:
    load_dotenv()
    tables = TableIds(
        sectors=os.environ["TABLE_ID_SECTORS"],
        tickers=os.environ["TABLE_ID_TICKERS"],
        indicators=os.environ["TABLE_ID_INDICATORS"],
        price_snapshots=os.environ["TABLE_ID_PRICE_SNAPSHOTS"],
        sector_news=os.environ["TABLE_ID_SECTOR_NEWS"],
        decisions=os.environ["TABLE_ID_DECISIONS"],
        trading_rules=os.environ["TABLE_ID_TRADING_RULES"],
    )
    return Config(
        feishu_app_id=os.environ["FEISHU_APP_ID"],
        feishu_app_secret=os.environ["FEISHU_APP_SECRET"],
        feishu_base_app_token=os.environ["FEISHU_BASE_APP_TOKEN"],
        tables=tables,
    )
```

- [ ] **Step 3：测试通过**

```bash
pytest tests/test_config.py -v
```

- [ ] **Step 4：提交**

```bash
git add scripts/config.py tests/test_config.py
git commit -m "feat: add config loader"
```

---

## Task 4：AkShare 数据抓取封装

**Files:**
- Create: `scripts/data_fetcher.py`
- Create: `tests/test_data_fetcher.py`

封装日/周/月 K 线抓取、板块新闻抓取、名称→代码查询。

- [ ] **Step 1：写失败测试 — 日线**

```python
import pandas as pd
from unittest.mock import patch
from scripts.data_fetcher import fetch_kline


def test_fetch_kline_daily_returns_dataframe():
    fake_df = pd.DataFrame({
        "日期": ["2026-05-06", "2026-05-07"],
        "开盘": [100.0, 101.0],
        "收盘": [101.0, 102.0],
        "最高": [102.0, 103.0],
        "最低": [99.5, 100.5],
        "成交量": [1000, 1100],
        "成交额": [101000, 112200],
    })
    with patch("scripts.data_fetcher.ak.stock_zh_a_hist", return_value=fake_df):
        out = fetch_kline("002594", period="日", days=2)

    assert len(out) == 2
    assert "close" in out.columns
    assert out.iloc[-1]["close"] == 102.0
```

- [ ] **Step 2：实现 `fetch_kline`**

```python
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta


PERIOD_MAP = {"日": "daily", "周": "weekly", "月": "monthly"}


def fetch_kline(code: str, period: str = "日", days: int = 250) -> pd.DataFrame:
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")  # 留 buffer
    raw = ak.stock_zh_a_hist(
        symbol=code,
        period=PERIOD_MAP[period],
        start_date=start,
        end_date=end,
        adjust="qfq",
    )
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.rename(columns={
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
    })
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True).tail(days).reset_index(drop=True)
    return df
```

- [ ] **Step 3：测试通过**

```bash
pytest tests/test_data_fetcher.py -v
```

- [ ] **Step 4：写失败测试 — 名称→代码**

```python
def test_resolve_code_by_name():
    fake = pd.DataFrame({"code": ["002594", "300750"], "name": ["比亚迪", "宁德时代"]})
    with patch("scripts.data_fetcher.ak.stock_info_a_code_name", return_value=fake):
        from scripts.data_fetcher import resolve_code
        assert resolve_code("比亚迪") == "002594"
        assert resolve_code("002594") == "002594"
        assert resolve_code("不存在") is None
```

- [ ] **Step 5：实现 `resolve_code`**

```python
def resolve_code(query: str) -> str | None:
    if query.isdigit() and len(query) == 6:
        return query
    table = ak.stock_info_a_code_name()
    hit = table[table["name"] == query]
    if not hit.empty:
        return hit.iloc[0]["code"]
    return None
```

- [ ] **Step 6：写失败测试 — 板块新闻**

```python
def test_fetch_sector_news_normalizes_fields():
    fake = pd.DataFrame({
        "标题": ["利好消息"],
        "摘要": ["..."],
        "来源": ["东方财富"],
        "链接": ["https://example.com/1"],
        "发布时间": ["2026-05-07 10:30:00"],
    })
    with patch("scripts.data_fetcher.ak.stock_news_em", return_value=fake):
        from scripts.data_fetcher import fetch_sector_news
        items = fetch_sector_news("CPO板块代码")
    assert items[0]["title"] == "利好消息"
    assert items[0]["url"] == "https://example.com/1"
```

- [ ] **Step 7：实现 `fetch_sector_news`**

注意：板块级新闻 AkShare 没有完美的统一接口，初版用关键词新闻 + 板块成分股新闻聚合。MVP 先用 `stock_news_em` 拿个股新闻、按板块聚合。

```python
def fetch_sector_news(sector_code: str, limit: int = 20) -> list[dict]:
    raw = ak.stock_news_em(symbol=sector_code)
    if raw is None or raw.empty:
        return []
    raw = raw.rename(columns={
        "标题": "title",
        "摘要": "summary",
        "来源": "source",
        "链接": "url",
        "发布时间": "published_at",
    })
    return raw.head(limit).to_dict(orient="records")
```

- [ ] **Step 8：跑测试通过**

```bash
pytest tests/test_data_fetcher.py -v
```

- [ ] **Step 9：用真实数据做一次 smoke test**

`scripts/_smoke_data.py`：

```python
from scripts.data_fetcher import fetch_kline, resolve_code

print(resolve_code("比亚迪"))
df = fetch_kline("002594", period="日", days=10)
print(df.tail())
```

```bash
python -m scripts._smoke_data
```

预期：打印 `002594` 和最近 10 个交易日的日线数据。

- [ ] **Step 10：提交**

```bash
git add scripts/data_fetcher.py tests/test_data_fetcher.py
git commit -m "feat: add AkShare data fetcher"
```

---

## Task 5：技术指标计算

**Files:**
- Create: `scripts/indicator_calc.py`
- Create: `tests/test_indicator_calc.py`

由配置驱动地算 MA / MACD / RSI / KDJ / BOLL，输出长格式行（适合写指标表）。

- [ ] **Step 1：写失败测试 — MA**

```python
import pandas as pd
from scripts.indicator_calc import compute_indicators


def make_df(closes):
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=len(closes)),
        "open": closes, "close": closes, "high": closes,
        "low": closes, "volume": [1] * len(closes), "amount": [1] * len(closes),
    })


def test_compute_indicators_includes_ma20():
    df = make_df([float(i) for i in range(1, 31)])
    rows = compute_indicators("002594", df, period="日", indicators=["MA5", "MA20"])
    names = {r["指标名"] for r in rows}
    assert names == {"MA5", "MA20"}
    ma20 = next(r for r in rows if r["指标名"] == "MA20")
    assert ma20["当前值"] == pytest.approx(sum(range(11, 31)) / 20)
```

- [ ] **Step 2：实现 `compute_indicators` 仅支持 MA**

```python
import pandas as pd
import pandas_ta as ta


def _ma(df: pd.DataFrame, length: int) -> pd.Series:
    return df["close"].rolling(length).mean()


def compute_indicators(code: str, df: pd.DataFrame, period: str, indicators: list[str]) -> list[dict]:
    if df is None or df.empty:
        return []
    out = []
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    for name in indicators:
        if name.startswith("MA"):
            length = int(name[2:])
            series = _ma(df, length)
            cur = float(series.iloc[-1]) if not pd.isna(series.iloc[-1]) else None
            prv = float(series.iloc[-2]) if len(series) >= 2 and not pd.isna(series.iloc[-2]) else None
            if cur is None:
                continue
            direction = "上行" if (prv is not None and cur > prv) else ("下行" if prv is not None and cur < prv else "横盘")
            out.append({
                "复合主键": f"{code}_{period}_{name}",
                "股票代码": code,
                "周期": period,
                "指标名": name,
                "当前值": round(cur, 4),
                "前值": round(prv, 4) if prv is not None else None,
                "信号状态": direction,
                "更新时间": str(last["date"].date()),
            })
    return out
```

- [ ] **Step 3：测试通过**

```bash
pytest tests/test_indicator_calc.py -v
```

- [ ] **Step 4：写失败测试 — MACD**

```python
def test_compute_indicators_includes_macd_dif_dea_hist():
    closes = [10.0 + 0.1 * i for i in range(60)]
    df = make_df(closes)
    rows = compute_indicators("002594", df, period="日", indicators=["MACD"])
    names = {r["指标名"] for r in rows}
    assert names == {"MACD-DIF", "MACD-DEA", "MACD-HIST"}
```

- [ ] **Step 5：扩展支持 MACD**

在 `compute_indicators` 中加分支：

```python
        elif name == "MACD":
            macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
            if macd is None or macd.empty:
                continue
            mapping = {
                "MACD-DIF": macd.columns[0],   # MACD_12_26_9
                "MACD-HIST": macd.columns[1],  # MACDh_12_26_9
                "MACD-DEA": macd.columns[2],   # MACDs_12_26_9
            }
            for sub_name, col in mapping.items():
                series = macd[col]
                cur = float(series.iloc[-1]) if not pd.isna(series.iloc[-1]) else None
                prv = float(series.iloc[-2]) if len(series) >= 2 and not pd.isna(series.iloc[-2]) else None
                if cur is None:
                    continue
                state = _macd_state(sub_name, cur, prv, macd)
                out.append({
                    "复合主键": f"{code}_{period}_{sub_name}",
                    "股票代码": code,
                    "周期": period,
                    "指标名": sub_name,
                    "当前值": round(cur, 4),
                    "前值": round(prv, 4) if prv is not None else None,
                    "信号状态": state,
                    "更新时间": str(last["date"].date()),
                })


def _macd_state(name: str, cur: float, prv: float | None, macd_df) -> str:
    if name != "MACD-HIST":
        return "上行" if (prv is not None and cur > prv) else "下行"
    # HIST 关注金叉死叉
    hist = macd_df[macd_df.columns[1]]
    if len(hist) < 2:
        return ""
    if hist.iloc[-2] <= 0 < hist.iloc[-1]:
        return "金叉(0日前)"
    if hist.iloc[-2] >= 0 > hist.iloc[-1]:
        return "死叉(0日前)"
    return "多头" if cur > 0 else "空头"
```

- [ ] **Step 6：测试通过**

```bash
pytest tests/test_indicator_calc.py -v
```

- [ ] **Step 7：写失败测试 — RSI/KDJ/BOLL**

```python
def test_compute_indicators_handles_rsi_kdj_boll():
    closes = [10.0 + 0.1 * i for i in range(60)]
    df = make_df(closes)
    rows = compute_indicators("002594", df, period="日",
                              indicators=["RSI14", "KDJ", "BOLL"])
    names = {r["指标名"] for r in rows}
    assert "RSI14" in names
    assert {"KDJ-K", "KDJ-D", "KDJ-J"}.issubset(names)
    assert {"BOLL-UPPER", "BOLL-MID", "BOLL-LOWER"}.issubset(names)
```

- [ ] **Step 8：扩展实现**

```python
        elif name == "RSI14":
            rsi = ta.rsi(df["close"], length=14)
            cur = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
            if cur is None:
                continue
            state = "超买" if cur > 80 else ("超卖" if cur < 20 else ("偏强" if cur > 50 else "偏弱"))
            out.append({
                "复合主键": f"{code}_{period}_RSI14",
                "股票代码": code,
                "周期": period,
                "指标名": "RSI14",
                "当前值": round(cur, 2),
                "前值": round(float(rsi.iloc[-2]), 2) if len(rsi) >= 2 and not pd.isna(rsi.iloc[-2]) else None,
                "信号状态": state,
                "更新时间": str(last["date"].date()),
            })
        elif name == "KDJ":
            kdj = ta.kdj(df["high"], df["low"], df["close"])
            for sub, col in zip(["KDJ-K", "KDJ-D", "KDJ-J"], kdj.columns):
                cur = float(kdj[col].iloc[-1]) if not pd.isna(kdj[col].iloc[-1]) else None
                if cur is None:
                    continue
                state = "高位" if cur > 80 else ("低位" if cur < 20 else "中位")
                out.append({
                    "复合主键": f"{code}_{period}_{sub}",
                    "股票代码": code,
                    "周期": period,
                    "指标名": sub,
                    "当前值": round(cur, 2),
                    "前值": None,
                    "信号状态": state,
                    "更新时间": str(last["date"].date()),
                })
        elif name == "BOLL":
            bb = ta.bbands(df["close"], length=20, std=2)
            mapping = {
                "BOLL-LOWER": bb.columns[0],
                "BOLL-MID": bb.columns[1],
                "BOLL-UPPER": bb.columns[2],
            }
            for sub, col in mapping.items():
                cur = float(bb[col].iloc[-1]) if not pd.isna(bb[col].iloc[-1]) else None
                if cur is None:
                    continue
                out.append({
                    "复合主键": f"{code}_{period}_{sub}",
                    "股票代码": code,
                    "周期": period,
                    "指标名": sub,
                    "当前值": round(cur, 2),
                    "前值": None,
                    "信号状态": "",
                    "更新时间": str(last["date"].date()),
                })
```

- [ ] **Step 9：跑全部测试**

```bash
pytest -v
```

- [ ] **Step 10：提交**

```bash
git add scripts/indicator_calc.py tests/test_indicator_calc.py
git commit -m "feat: add configurable technical indicators"
```

---

## Task 6：主流程编排

**Files:**
- Create: `scripts/main.py`
- Create: `tests/test_main.py`

按规范文档 5.1 节的关键执行步骤编排：拉股票→算指标→写表→滚动清理。

- [ ] **Step 1：写失败测试 — 单只股票全周期处理**

```python
from unittest.mock import MagicMock, patch
import pandas as pd
from scripts.main import process_ticker


def test_process_ticker_writes_indicators_for_all_periods():
    df = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=30),
        "open": range(30), "close": range(30), "high": range(30),
        "low": range(30), "volume": [1] * 30, "amount": [1] * 30,
    })
    bitable = MagicMock()
    cfg = MagicMock()
    cfg.indicators_by_period = {"日": ["MA5"], "周": ["MA4"], "月": ["MA6"]}
    cfg.tables.indicators = "tbl_ind"
    cfg.tables.price_snapshots = "tbl_snap"
    cfg.tables.tickers = "tbl_tk"

    with patch("scripts.main.fetch_kline", return_value=df):
        process_ticker(
            ticker={"record_id": "rec1", "fields": {"股票代码": "002594", "股票名称": "比亚迪", "所属板块": [{"text": "电池"}]}},
            cfg=cfg,
            bitable=bitable,
        )

    # 应分别写日/周/月指标，至少 3 次 batch_create 到 tbl_ind
    create_calls = [c for c in bitable.batch_create.call_args_list if c.args[0] == "tbl_ind"]
    assert len(create_calls) == 3
```

- [ ] **Step 2：实现 `process_ticker`（最小版）**

```python
from scripts.data_fetcher import fetch_kline
from scripts.indicator_calc import compute_indicators


def process_ticker(ticker: dict, cfg, bitable) -> None:
    code = ticker["fields"]["股票代码"]
    record_id = ticker["record_id"]
    last_close = None

    for period, indicator_list in cfg.indicators_by_period.items():
        df = fetch_kline(code, period=period, days=250)
        if df is None or df.empty:
            continue
        rows = compute_indicators(code, df, period=period, indicators=indicator_list)
        if rows:
            # 先删该 (代码, 周期) 旧值
            old = bitable.list_records(
                cfg.tables.indicators,
                filter_=f'AND(CurrentValue.[股票代码] = "{code}", CurrentValue.[周期] = "{period}")',
            )
            if old:
                bitable.batch_delete(cfg.tables.indicators, [r["record_id"] for r in old])
            bitable.batch_create(cfg.tables.indicators, rows)

        # 只在日线时更新行情快照和标的表
        if period == "日":
            last_close = float(df.iloc[-1]["close"])
            snapshot_row = {
                "复合主键": f"{code}_{df.iloc[-1]['date'].strftime('%Y%m%d')}",
                "股票代码": code,
                "交易日": str(df.iloc[-1]["date"].date()),
                "开盘价": float(df.iloc[-1]["open"]),
                "收盘价": last_close,
                "最高价": float(df.iloc[-1]["high"]),
                "最低价": float(df.iloc[-1]["low"]),
                "成交量": float(df.iloc[-1]["volume"]),
                "成交额": float(df.iloc[-1]["amount"]),
            }
            bitable.batch_create(cfg.tables.price_snapshots, [snapshot_row])

            # 更新标的表的当日数据
            change_pct = (last_close / float(df.iloc[-2]["close"]) - 1) * 100 if len(df) >= 2 else 0
            high_60 = float(df.tail(60)["high"].max())
            low_60 = float(df.tail(60)["low"].min())
            bitable.update_record(cfg.tables.tickers, record_id, {
                "最新收盘价": last_close,
                "当日涨跌幅": round(change_pct, 2),
                "当日成交量": float(df.iloc[-1]["volume"]),
                "60日最高": high_60,
                "60日最低": low_60,
                "距高点回撤%": round((last_close / high_60 - 1) * 100, 2),
                "最后更新时间": str(df.iloc[-1]["date"].date()),
            })
```

- [ ] **Step 3：在 `BitableClient` 添加 `update_record` 方法**

`scripts/bitable_client.py` 追加：

```python
    def update_record(self, table_id: str, record_id: str, fields: dict) -> None:
        url = f"{self.BASE_URL}/bitable/v1/apps/{self.base_app_token}/tables/{table_id}/records/{record_id}"
        resp = requests.put(url, headers=self._auth_headers(), json={"fields": fields}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu update_record error: {data}")
```

补一个测试：

```python
def test_update_record_calls_put():
    fake = MagicMock()
    fake.json.return_value = {"code": 0}
    fake.raise_for_status = MagicMock()
    with patch("scripts.bitable_client.requests.put", return_value=fake) as mp:
        with patch.object(BitableClient, "_get_tenant_access_token", return_value="t"):
            BitableClient("id", "secret", "bt").update_record("tbl", "rec1", {"a": 1})
    assert mp.called
```

- [ ] **Step 4：跑测试**

```bash
pytest -v
```

- [ ] **Step 5：写失败测试 — 滚动清理**

```python
def test_cleanup_removes_old_snapshots():
    from scripts.main import cleanup_rolling_window
    bitable = MagicMock()
    bitable.list_records.return_value = [
        {"record_id": "r1", "fields": {"交易日": "2025-01-01"}},
        {"record_id": "r2", "fields": {"交易日": "2026-05-01"}},
    ]
    cfg = MagicMock()
    cfg.tables.price_snapshots = "tbl_snap"
    cfg.snapshot_window_days = 90

    cleanup_rolling_window(cfg, bitable, today="2026-05-07")

    bitable.batch_delete.assert_called_once()
    deleted_ids = bitable.batch_delete.call_args.args[1]
    assert "r1" in deleted_ids
    assert "r2" not in deleted_ids
```

- [ ] **Step 6：实现 `cleanup_rolling_window`**

```python
from datetime import datetime, timedelta


def cleanup_rolling_window(cfg, bitable, today: str | None = None) -> None:
    today_dt = datetime.fromisoformat(today) if today else datetime.now()
    snap_cutoff = (today_dt - timedelta(days=cfg.snapshot_window_days)).date().isoformat()
    news_cutoff = (today_dt - timedelta(days=cfg.news_window_days)).date().isoformat()

    # 行情快照
    snaps = bitable.list_records(cfg.tables.price_snapshots)
    expired = [r["record_id"] for r in snaps
               if r["fields"].get("交易日", "9999-12-31") < snap_cutoff]
    if expired:
        bitable.batch_delete(cfg.tables.price_snapshots, expired)

    # 新闻
    news = bitable.list_records(cfg.tables.sector_news)
    expired = [r["record_id"] for r in news
               if (r["fields"].get("发布时间", "")[:10] or "9999-12-31") < news_cutoff]
    if expired:
        bitable.batch_delete(cfg.tables.sector_news, expired)
```

- [ ] **Step 7：实现 `main()` 主入口**

`scripts/main.py` 末尾追加：

```python
import logging
import traceback
from scripts.config import load_config
from scripts.bitable_client import BitableClient
from scripts.data_fetcher import fetch_sector_news


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    bitable = BitableClient(cfg.feishu_app_id, cfg.feishu_app_secret, cfg.feishu_base_app_token)

    tickers = bitable.list_records(cfg.tables.tickers)
    logging.info(f"Loaded {len(tickers)} tickers")

    failed = []
    for t in tickers:
        code = t["fields"].get("股票代码", "")
        try:
            process_ticker(t, cfg, bitable)
            logging.info(f"OK: {code}")
        except Exception as e:
            logging.error(f"FAIL {code}: {e}\n{traceback.format_exc()}")
            failed.append((code, str(e)))

    # 板块新闻
    sectors = bitable.list_records(cfg.tables.sectors)
    for s in sectors:
        sector_code = s["fields"].get("板块代码")
        sector_name = s["fields"].get("板块名")
        if not sector_code:
            continue
        try:
            news = fetch_sector_news(sector_code)
            rows = [{
                "板块名": [sector_name],
                "标题": n.get("title"),
                "摘要": n.get("summary"),
                "来源": n.get("source"),
                "URL": n.get("url"),
                "发布时间": n.get("published_at"),
            } for n in news]
            if rows:
                bitable.batch_create(cfg.tables.sector_news, rows)
            logging.info(f"News OK: {sector_name}")
        except Exception as e:
            logging.error(f"News FAIL {sector_name}: {e}")

    cleanup_rolling_window(cfg, bitable)

    if failed:
        logging.warning(f"Failures: {failed}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 8：跑测试**

```bash
pytest -v
```

- [ ] **Step 9：本地端到端 dry run**

确保 `.env` 已配好（Task 1 Step 7）和标的表至少有 1-2 只测试股票。

```bash
python -m scripts.main
```

预期：日志显示每只股票 OK，飞书 Bitable 中指标表、行情快照表、标的表的字段被填充。

- [ ] **Step 10：提交**

```bash
git add scripts/main.py scripts/bitable_client.py tests/
git commit -m "feat: orchestrate daily data update flow"
git push
```

---

## Task 7：GitHub Actions 定时任务

**Files:**
- Create: `.github/workflows/daily.yml`

每个交易日 15:30（北京时间）自动跑。

- [ ] **Step 1：在 GitHub 仓库 Settings → Secrets 添加密钥**

清单（与 `.env` 一致）：
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_BASE_APP_TOKEN`
- `TABLE_ID_SECTORS`
- `TABLE_ID_TICKERS`
- `TABLE_ID_INDICATORS`
- `TABLE_ID_PRICE_SNAPSHOTS`
- `TABLE_ID_SECTOR_NEWS`
- `TABLE_ID_DECISIONS`
- `TABLE_ID_TRADING_RULES`

- [ ] **Step 2：创建 workflow 文件**

`.github/workflows/daily.yml`：

```yaml
name: Daily Investment Data Update

on:
  schedule:
    # 北京时间 15:30 = UTC 07:30，工作日（周一-周五）
    - cron: "30 7 * * 1-5"
  workflow_dispatch:  # 允许手动触发

concurrency:
  group: daily-update
  cancel-in-progress: false

jobs:
  update:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install deps
        run: pip install -r requirements.txt

      - name: Run daily update
        env:
          FEISHU_APP_ID: ${{ secrets.FEISHU_APP_ID }}
          FEISHU_APP_SECRET: ${{ secrets.FEISHU_APP_SECRET }}
          FEISHU_BASE_APP_TOKEN: ${{ secrets.FEISHU_BASE_APP_TOKEN }}
          TABLE_ID_SECTORS: ${{ secrets.TABLE_ID_SECTORS }}
          TABLE_ID_TICKERS: ${{ secrets.TABLE_ID_TICKERS }}
          TABLE_ID_INDICATORS: ${{ secrets.TABLE_ID_INDICATORS }}
          TABLE_ID_PRICE_SNAPSHOTS: ${{ secrets.TABLE_ID_PRICE_SNAPSHOTS }}
          TABLE_ID_SECTOR_NEWS: ${{ secrets.TABLE_ID_SECTOR_NEWS }}
          TABLE_ID_DECISIONS: ${{ secrets.TABLE_ID_DECISIONS }}
          TABLE_ID_TRADING_RULES: ${{ secrets.TABLE_ID_TRADING_RULES }}
        run: python -m scripts.main

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: failure-logs
          path: "*.log"
          retention-days: 7
```

- [ ] **Step 3：提交并触发手动运行**

```bash
git add .github/workflows/daily.yml
git commit -m "ci: add daily Bitable update workflow"
git push
```

操作：GitHub 仓库 → Actions → "Daily Investment Data Update" → Run workflow → 等待执行。

- [ ] **Step 4：验证**

到飞书 Bitable 看：
- 标的表的"最新收盘价/涨跌幅/最后更新时间"是否填充
- 指标表是否有数据，按周期分布
- 行情快照表是否有当日数据
- 板块新闻表是否有近期新闻

如有失败，下载 Actions 日志定位。

- [ ] **Step 5：提交（如有 fix）**

```bash
git add -p
git commit -m "fix: <具体修复点>"
git push
```

---

## Task 8：里程碑 1 验收 Smoke Test

- [ ] **Step 1：连续观察 3 个交易日的 GitHub Actions 运行**

每天 15:30 后查看 Actions 状态：
- ✅ 全部成功 → 进入里程碑 2
- ⚠️ 某只股票失败 → 在脚本日志找原因，修复后回到 Task 6 继续

- [ ] **Step 2：检查数据完整性**

在飞书 Bitable 检查：
- 指标表行数 ≈ 标的数 × 3 周期 × 配置的指标数（每只股票每个周期完整）
- 行情快照表行数 = 标的数 × 已运行天数
- 板块新闻表有当日新闻

- [ ] **Step 3：性能检查**

在飞书 App 中打开 Bitable 各视图，确认 < 3 秒打开。

里程碑 1 完成 ✅

---

## Task 9：Dify Cloud 工作区与 Knowledge 内容

**Files:**
- Create: `docs/dify-knowledge/trading_rules.md`
- Create: `docs/dify-knowledge/kol_views.md`
- Create: `docs/dify-knowledge/stock_basics.md`

- [ ] **Step 1：注册 Dify Cloud**

操作：访问 https://dify.ai → 注册账号 → 创建工作空间"NowItsYourChoice"。

- [ ] **Step 2：在 Dify 设置中接入 DeepSeek-V3**

操作：Dify → 设置 → 模型供应商 → DeepSeek → 填入 API Key（在 https://platform.deepseek.com 申请）。

- [ ] **Step 3：创建三个 Knowledge 库**

在 Dify → 知识库 新建：
- `knowledge_trading_rules`（分段方式：自定义，最大长度 500，分段标识 `\n\n`）
- `knowledge_kol_views`（分段方式：自动）
- `knowledge_stock_basics`（分段方式：自动）

每个都选 Embedding 模型为 DeepSeek 内置 embedding 或 Dify 默认模型。

- [ ] **Step 4：本地准备 `trading_rules.md`**

把 Bitable 交易纪律表的初始 10-20 条整理成 Markdown，每条用 `##` 分段：

```markdown
## 单股仓位上限不超过总仓位的 20%

**类型**：仓位管理
**优先级**：必守
**详细描述**：任何单只股票的持仓金额不超过我总投资金额的 20%，避免单一标的暴雷拖垮整体。
**触发场景**：买入或加仓时检查。

## 跌破 20 日线减仓 50%

**类型**：止损
**优先级**：必守
**详细描述**：持仓股票收盘价跌破 20 日均线（日线），第二个交易日开盘减仓一半。
**触发场景**：日线收盘价 < MA20 时。

...（其余条目）
```

- [ ] **Step 5：上传到 `knowledge_trading_rules`**

操作：Dify 知识库 `knowledge_trading_rules` → 添加文档 → 上传 `trading_rules.md`。

确认：上传后查看分段，每条规则是独立 chunk。

- [ ] **Step 6：上传初始大 V 观点和股票知识（可空文件起步）**

`docs/dify-knowledge/kol_views.md`、`stock_basics.md` 先各放一段占位文本，上传到对应库（后续阶段持续补充）。

- [ ] **Step 7：提交**

```bash
git add docs/dify-knowledge/
git commit -m "docs: add initial Dify Knowledge contents"
git push
```

---

## Task 10：Dify 决策引擎工作流

**说明：** 此 Task 是在 Dify Cloud Web 界面上的图形化配置。每个步骤是 Dify 中的具体操作。

- [ ] **Step 1：创建 Chatflow 应用**

操作：Dify → 应用 → 创建空白应用 → 选 **Chatflow**（不是 Workflow，因为我们要用 Dify 自带的对话 UI 让用户在浏览器/手机直接发消息；Chatflow 内部仍可用所有 Workflow 节点） → 命名"决策引擎"。

- [ ] **Step 2：定义工作流输入参数**

在"开始"节点，添加参数：
- `ticker_code`（文本，必填）：股票代码
- `user_question`（文本，选填）：用户的具体问题

- [ ] **Step 3：节点 2 — 拉标的基础信息**

添加"HTTP 请求"节点，名称"查标的"。
- Method：GET
- URL：`https://open.feishu.cn/open-apis/bitable/v1/apps/{base_app_token}/tables/{table_id_tickers}/records`
- Query 参数：`filter` = `CurrentValue.[股票代码]="{{#start.ticker_code#}}"`
- Headers：`Authorization: Bearer {{tenant_access_token}}`
- 注意：`tenant_access_token` 通过另一个 HTTP 节点获取，或用 Dify 的"凭证管理"功能。

**简化做法**：先做一个独立的"获取 Token"节点：
- POST `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
- Body：`{"app_id": "{{env.FEISHU_APP_ID}}", "app_secret": "{{env.FEISHU_APP_SECRET}}"}`
- 输出变量：`token`

- [ ] **Step 4：节点 3 — 拉指标表**

添加"HTTP 请求"节点，名称"查指标"。
- GET `.../tables/{indicators_table_id}/records`
- filter：`CurrentValue.[股票代码]="{{#start.ticker_code#}}"`
- 输出 JSON 解析成 items 数组

- [ ] **Step 5：节点 4 — 拉板块新闻**

先加"代码"节点，名称"提取板块"，从节点 2 的标的输出 JSON 中取出板块名（标的表的"所属板块"是关联字段，返回数组）：

```python
def main(ticker_response: dict) -> dict:
    items = ticker_response.get("data", {}).get("items", [])
    if not items:
        return {"sector_name": ""}
    sectors = items[0].get("fields", {}).get("所属板块", [])
    if isinstance(sectors, list) and sectors:
        first = sectors[0]
        return {"sector_name": first.get("text") if isinstance(first, dict) else str(first)}
    return {"sector_name": ""}
```

再加"HTTP 请求"节点查板块新闻表：
- GET `.../tables/{sector_news_table_id}/records`
- filter：`AND(CurrentValue.[板块名] = "{{#提取板块.sector_name#}}", CurrentValue.[发布时间] > TODAY()-7)`
- 输出 JSON 解析成 news_items 数组

- [ ] **Step 6：节点 5 — 召回交易纪律**

添加"知识检索"节点：
- 选择 `knowledge_trading_rules`
- 查询：`{{#start.ticker_code#}} {{#查标的.板块#}} 交易纪律`
- TopK：5

- [ ] **Step 7：节点 6 — 召回相关知识**

添加另一个"知识检索"节点：
- 选择 `knowledge_stock_basics` 和 `knowledge_kol_views`
- 查询：`{{#查标的.板块#}} {{#start.user_question#}}`
- TopK：3

- [ ] **Step 8：节点 7+8 — 调用 DeepSeek 生成建议**

添加"LLM"节点：
- 模型：DeepSeek-V3
- Temperature：0.3（追求稳定输出）
- Max Tokens：2000

**System Prompt**（直接粘贴）：

```
你是一位严谨的 A 股投资分析助手。基于多周期技术指标、板块新闻、用户的交易纪律，给出操作建议。
保持中立审慎；明确指出关键数据；信息不充分时直接说明。
输出严格按照「## 操作建议 / ## 关键依据 / ## 风险提示 / ## 适用纪律」四段 Markdown 格式。
```

**User Prompt 模板**（用 Dify 的变量插值语法 `{{#节点.字段#}}` 拼装）：

```
# 标的基础信息
板块：{{#提取板块.sector_name#}}
最新收盘价：{{#查标的.body.data.items[0].fields.最新收盘价#}}
当日涨跌幅：{{#查标的.body.data.items[0].fields.当日涨跌幅#}}%
60 日最高：{{#查标的.body.data.items[0].fields.60日最高#}}
距高点回撤：{{#查标的.body.data.items[0].fields.距高点回撤%#}}%
当前持有：{{#查标的.body.data.items[0].fields.当前持有#}}（成本：{{#查标的.body.data.items[0].fields.成本价#}}）

# 多周期技术指标
{{#查指标.body.data.items#}}（Dify 会把 items 数组每行展开为 `指标名 周期 当前值 信号状态`）

# 板块近期新闻（最近 7 天）
{{#查新闻.body.data.items#}}（每条 `标题 - 来源 - 发布时间`）

# 适用的交易纪律
{{#召回纪律.result#}}

# 相关投资知识
{{#召回知识.result#}}

# 用户问题
{{#start.user_question#}}（若空，则回答"该如何操作？"）

请严格按四段格式输出。
```

完整模板对照规范文档第 5.3 节末尾的 Prompt 框架。

- [ ] **Step 9：节点 9 — 解析输出**

添加"代码"节点（Python），按 markdown 标题切分为 `操作建议 / 关键依据 / 风险提示 / 适用纪律` 四段。

```python
def main(llm_output: str) -> dict:
    sections = {"操作建议": "", "关键依据": "", "风险提示": "", "适用纪律": ""}
    current = None
    for line in llm_output.split("\n"):
        s = line.strip()
        if s.startswith("##"):
            for k in sections:
                if k in s:
                    current = k
                    break
        elif current:
            sections[current] += line + "\n"
    return {"sections": {k: v.strip() for k, v in sections.items()}, "raw": llm_output}
```

- [ ] **Step 10：节点 10 — 写回决策记录**

HTTP 请求节点，POST 到决策记录表的 batch_create，把四段内容、ticker_code、user_question、当时指标快照（节点 3 的输出 JSON 字符串）一并写入。

- [ ] **Step 11：节点 11 — 输出**

"结束"节点：返回 `result_text` = 拼接四段格式化文本，飞书 Bot 直接发出去。

- [ ] **Step 12：测试运行**

在 Dify 工作流编辑器右上角"运行"，输入 `ticker_code = 002594`，观察各节点输出和最终回复。

确保：
- 各 HTTP 节点返回 200 + 数据
- LLM 输出包含四段
- 决策记录表中出现新行

- [ ] **Step 13：发布工作流**

点击"发布" → 拿到 API URL 和 API Key（用于飞书 Bot 调用）。

- [ ] **Step 14：提交（仅记录文档）**

```bash
mkdir -p docs/dify-config
echo "Decision engine workflow published. API: <url>" > docs/dify-config/decision-engine.md
git add docs/dify-config/
git commit -m "docs: record Dify decision engine workflow setup"
git push
```

---

## Task 11：飞书 Bot 接入 Dify

- [ ] **Step 1：在飞书开放平台配置事件订阅**

操作：开发者后台 → 应用 → 事件订阅。
- 订阅方式：长连接（推荐）或回调地址
- 订阅事件：`接收消息 v2.0`（`im.message.receive_v1`）

如果选回调地址，需要一个公网 webhook。**推荐用长连接（飞书提供 SDK）**——但这要求长连接服务一直跑，又回到了"需要服务器"的问题。

**MVP 折中方案**：用 Dify 自带的"对话型应用"包装，直接给用户一个 Web 链接（在 Dify Cloud 上），暂不接入飞书 Bot。

操作：
1. 在 Dify 中复制工作流为"对话应用"
2. 发布后 Dify 给一个公网 URL，比如 `https://udify.app/chatbot/xxxxx`
3. 飞书 Bot 这一步推迟到阶段 1.5（如有需要再做）

记录此决定：

```bash
echo "MVP 用 Dify 自带对话页面，飞书 Bot 接入推迟到阶段 1.5" >> docs/dify-config/decision-engine.md
```

- [ ] **Step 2：配置开场白和示例问题**

由于 Task 10 已经把决策引擎做成 Chatflow，这一步直接在它的"功能"或"开场白"配置中加：

开场白：

> 你好！发送股票代码（如 `002594`）或股票名称（如 `比亚迪`），我会基于多周期技术指标、板块新闻、交易纪律给出操作建议。

示例问题：
- `$002594`
- `宁德时代`
- `比亚迪 该减仓吗`

- [ ] **Step 3：发布并测试**

操作：Dify → 应用 → 概览 → 公开访问 → 启用。

在手机和电脑浏览器打开公开 URL，发送 `002594`，验证 5-10 秒内得到完整决策回复。

- [ ] **Step 4：把链接保存到飞书 Bitable 标的表的"备注"或独立"快捷链接"**

让你以后不用记网址，从飞书 Bitable 一键打开决策对话。

- [ ] **Step 5：（可选）后续阶段 1.5 — 真正的飞书 Bot 接入**

记录 TODO：

```markdown
## 阶段 1.5（可选）：飞书 Bot 长连接接入
- 用 Cloudflare Workers 或 Vercel Functions 跑长连接 SDK
- 接收消息后调 Dify Workflow API
- 推送决策结果回飞书群/私聊
```

写入 `docs/dify-config/decision-engine.md`，git 提交。

```bash
git add docs/dify-config/decision-engine.md
git commit -m "docs: defer Feishu Bot integration to phase 1.5"
git push
```

---

## Task 12：里程碑 2 端到端验收

按规范文档第 9 节的验收标准逐项核对：

- [ ] **Step 1：GitHub Actions 连续 5 个交易日 100% 成功**

查看 Actions 历史，确认无失败。

- [ ] **Step 2：Bitable 数据齐全**

- 标的表：所有股票当日字段已填
- 指标表：每只股票每个周期都有完整指标行
- 行情快照表：每只股票最近 5 个交易日的快照
- 板块新闻表：每个板块都有近期新闻

- [ ] **Step 3：决策引擎响应**

在 Dify 公开 URL 测试：
- 发送 `002594` → 10 秒内收到包含"操作建议/关键依据/风险提示/适用纪律"四段的回复
- 发送 `比亚迪` → 同上（验证名称→代码转换）
- 发送 `不在关注列表的股票，如 600519` → 回复中标注"未纳入日常关注"

- [ ] **Step 4：决策记录入库**

Bitable 决策记录表中能看到刚才的每次问询。

- [ ] **Step 5：看板视图加载性能**

在飞书 App 中分别打开"关注标的""板块概览""今日新闻""走势图"视图，每个 < 3 秒。

- [ ] **Step 6：Knowledge RAG 召回**

在 Dify 工作流的"知识检索"节点的运行历史中，确认每次有交易纪律和投资知识被召回到 prompt 中。

- [ ] **Step 7：完成总结**

```bash
cat > docs/phase1-completion.md <<'EOF'
# 阶段 1 完成总结
- 数据管道：每日 15:30 GitHub Actions 自动跑
- Bitable 数据：标的/指标/快照/新闻全部齐全
- Dify 决策引擎：发布在 https://udify.app/chatbot/<id>
- Dify Knowledge：交易纪律、KOL 观点、投资知识三库已建
- 进入阶段 2：总资产看板 + 持仓更新
EOF
git add docs/phase1-completion.md
git commit -m "docs: phase 1 completion record"
git push
```

阶段 1 完成 ✅

---

## 自查清单（计划完成后开发者参考）

- [ ] 所有 Python 测试通过 (`pytest -v` 全绿)
- [ ] `.env` 不在 git 中
- [ ] GitHub Secrets 全部配齐
- [ ] Actions 连续 5 个交易日成功
- [ ] Bitable 看板视图全部 < 3 秒打开
- [ ] Dify 公开 URL 能正常返回决策建议
- [ ] 决策回复包含四个段落
- [ ] 知识库召回内容相关性合理
- [ ] 决策记录表持续累积

---

## 反模式提醒（实施过程中明确避免）

- ❌ 不要把数据 commit 进 repo
- ❌ 不要在 Bitable 用大量跨表 lookup 公式
- ❌ 不要在 Dify 工作流硬编码股票代码或板块名
- ❌ 不要在指标表用宽表（一指标一列）
- ❌ 不要让单只股票的失败影响整体跑批
- ❌ 不要把飞书 App Secret 写进代码或日志
