"""One-shot Bitable schema sync script.

Populates each of the 7 NIYC Bitable tables with the field schema defined
in code. Idempotent: existing fields are skipped, missing fields are
created. The default first field of an empty Feishu table is type=1 text;
its name can be changed but its type cannot. We rename it to match the
schema's first field name.
"""
import os
from dataclasses import dataclass, field as _df

import requests
from dotenv import load_dotenv

from scripts.bitable_client import BitableClient


FT_TEXT = 1
FT_NUMBER = 2
FT_SINGLE_SELECT = 3
FT_DATE_TIME = 5
FT_URL = 15
FT_DUPLEX_LINK = 21

DATE_PROP = {"date_formatter": "yyyy/MM/dd", "auto_fill": False}
DATETIME_PROP = {"date_formatter": "yyyy/MM/dd HH:mm", "auto_fill": False}


@dataclass
class FieldDef:
    name: str
    type: int
    property: dict = _df(default_factory=dict)


def schema_for_sectors() -> list[FieldDef]:
    return [
        FieldDef("板块名", FT_TEXT),
        FieldDef("板块代码", FT_TEXT),
        FieldDef("关注度", FT_SINGLE_SELECT, {"options": [{"name": "高"}, {"name": "中"}, {"name": "低"}]}),
        FieldDef("备注", FT_TEXT),
    ]


def schema_for_tickers(sectors_table_id: str) -> list[FieldDef]:
    return [
        FieldDef("股票代码", FT_TEXT),
        FieldDef("股票名称", FT_TEXT),
        FieldDef("所属板块", FT_DUPLEX_LINK, {"table_id": sectors_table_id, "multiple": True}),
        FieldDef("当前持有", FT_NUMBER),
        FieldDef("成本价", FT_NUMBER),
        FieldDef("最新收盘价", FT_NUMBER),
        FieldDef("当日涨跌幅", FT_NUMBER),
        FieldDef("当日成交量", FT_NUMBER),
        FieldDef("60日最高", FT_NUMBER),
        FieldDef("60日最低", FT_NUMBER),
        FieldDef("距高点回撤%", FT_NUMBER),
        FieldDef("最后更新时间", FT_DATE_TIME, dict(DATETIME_PROP)),
    ]


def schema_for_indicators() -> list[FieldDef]:
    indicator_options = [
        "MA5", "MA10", "MA20", "MA60", "MA4", "MA13", "MA26", "MA6", "MA12",
        "MACD-DIF", "MACD-DEA", "MACD-HIST",
        "RSI14",
        "KDJ-K", "KDJ-D", "KDJ-J",
        "BOLL-UPPER", "BOLL-MID", "BOLL-LOWER",
    ]
    return [
        FieldDef("复合主键", FT_TEXT),
        FieldDef("股票代码", FT_TEXT),
        FieldDef("周期", FT_SINGLE_SELECT, {"options": [{"name": "日"}, {"name": "周"}, {"name": "月"}]}),
        FieldDef("指标名", FT_SINGLE_SELECT, {"options": [{"name": n} for n in indicator_options]}),
        FieldDef("当前值", FT_NUMBER),
        FieldDef("前值", FT_NUMBER),
        FieldDef("信号状态", FT_TEXT),
        FieldDef("更新时间", FT_DATE_TIME, dict(DATETIME_PROP)),
    ]


def schema_for_price_snapshots() -> list[FieldDef]:
    return [
        FieldDef("复合主键", FT_TEXT),
        FieldDef("股票代码", FT_TEXT),
        FieldDef("交易日", FT_DATE_TIME, dict(DATE_PROP)),
        FieldDef("开盘价", FT_NUMBER),
        FieldDef("收盘价", FT_NUMBER),
        FieldDef("最高价", FT_NUMBER),
        FieldDef("最低价", FT_NUMBER),
        FieldDef("成交量", FT_NUMBER),
        FieldDef("成交额", FT_NUMBER),
    ]


def schema_for_sector_news(sectors_table_id: str) -> list[FieldDef]:
    return [
        FieldDef("标题", FT_TEXT),
        FieldDef("板块名", FT_DUPLEX_LINK, {"table_id": sectors_table_id, "multiple": True}),
        FieldDef("摘要", FT_TEXT),
        FieldDef("来源", FT_TEXT),
        FieldDef("URL", FT_URL),
        FieldDef("发布时间", FT_DATE_TIME, dict(DATETIME_PROP)),
        FieldDef("情感倾向", FT_SINGLE_SELECT, {"options": [{"name": "正面"}, {"name": "中性"}, {"name": "负面"}]}),
    ]


def schema_for_decisions() -> list[FieldDef]:
    # NOTE: spec listed 决策时间 as primary (date_time), but Feishu does
    # not allow changing the default field's type. Default is text, so
    # 决策时间 stays as primary in the visual sense but its type is text.
    # Decisions write ISO date strings (e.g. "2026-05-08 14:30:00") into it.
    return [
        FieldDef("决策时间", FT_TEXT),
        FieldDef("股票代码", FT_TEXT),
        FieldDef("用户问题", FT_TEXT),
        FieldDef("操作建议", FT_TEXT),
        FieldDef("关键依据", FT_TEXT),
        FieldDef("风险提示", FT_TEXT),
        FieldDef("当时指标快照", FT_TEXT),
        FieldDef("用户实际操作", FT_SINGLE_SELECT, {"options": [
            {"name": "待填"}, {"name": "买入"}, {"name": "卖出"},
            {"name": "加仓"}, {"name": "减仓"}, {"name": "不操作"},
        ]}),
    ]


def schema_for_trading_rules() -> list[FieldDef]:
    return [
        FieldDef("纪律标题", FT_TEXT),
        FieldDef("详细描述", FT_TEXT),
        FieldDef("类型", FT_SINGLE_SELECT, {"options": [
            {"name": "仓位管理"}, {"name": "进场"}, {"name": "止损"},
            {"name": "止盈"}, {"name": "心态"},
        ]}),
        FieldDef("优先级", FT_SINGLE_SELECT, {"options": [
            {"name": "必守"}, {"name": "重要"}, {"name": "参考"},
        ]}),
        FieldDef("状态", FT_SINGLE_SELECT, {"options": [
            {"name": "启用"}, {"name": "停用"},
        ]}),
    ]


def schema_for_trades() -> list[FieldDef]:
    return [
        FieldDef("交易时间", FT_DATE_TIME, dict(DATETIME_PROP)),
        FieldDef("股票代码", FT_TEXT),
        FieldDef("股票名称", FT_TEXT),
        FieldDef("方向", FT_SINGLE_SELECT, {"options": [
            {"name": "买入"}, {"name": "卖出"},
        ]}),
        FieldDef("成交价", FT_NUMBER),
        FieldDef("成交数量", FT_NUMBER),
        FieldDef("成交金额", FT_NUMBER),
        FieldDef("佣金", FT_NUMBER),
        FieldDef("印花税", FT_NUMBER),
        FieldDef("过户费", FT_NUMBER),
        FieldDef("手续费合计", FT_NUMBER),
        FieldDef("券商", FT_SINGLE_SELECT, {"options": [
            {"name": "招商"}, {"name": "华泰"},
        ]}),
        FieldDef("来源", FT_SINGLE_SELECT, {"options": [
            {"name": "截图识别"}, {"name": "手动录入"},
        ]}),
        FieldDef("识别状态", FT_SINGLE_SELECT, {"options": [
            {"name": "已确认"}, {"name": "待确认"}, {"name": "识别失败"},
        ]}),
    ]


def schema_for_portfolio(sectors_table_id: str) -> list[FieldDef]:
    return [
        FieldDef("股票代码", FT_TEXT),
        FieldDef("股票名称", FT_TEXT),
        FieldDef("券商", FT_SINGLE_SELECT, {"options": [
            {"name": "招商"}, {"name": "华泰"},
        ]}),
        FieldDef("资金属性", FT_SINGLE_SELECT, {"options": [
            {"name": "自有"}, {"name": "代管"},
        ]}),
        FieldDef("所属板块", FT_DUPLEX_LINK, {"table_id": sectors_table_id, "multiple": True}),
        FieldDef("持仓数量", FT_NUMBER),
        FieldDef("成本价", FT_NUMBER),
        FieldDef("成本金额", FT_NUMBER),
        FieldDef("当前价", FT_NUMBER),
        FieldDef("市值", FT_NUMBER),
        FieldDef("浮盈额", FT_NUMBER),
        FieldDef("浮盈%", FT_NUMBER),
        FieldDef("仓位占比%", FT_NUMBER),
        FieldDef("仓位预警", FT_SINGLE_SELECT, {"options": [
            {"name": "正常"}, {"name": "超标"},
        ]}),
    ]


def schema_for_asset_snapshots() -> list[FieldDef]:
    return [
        FieldDef("日期", FT_DATE_TIME, dict(DATE_PROP)),
        FieldDef("券商", FT_SINGLE_SELECT, {"options": [
            {"name": "招商"}, {"name": "华泰"}, {"name": "全部"},
        ]}),
        FieldDef("资金属性", FT_SINGLE_SELECT, {"options": [
            {"name": "自有"}, {"name": "代管"}, {"name": "全部"},
        ]}),
        FieldDef("总市值", FT_NUMBER),
        FieldDef("总成本", FT_NUMBER),
        FieldDef("总浮盈", FT_NUMBER),
        FieldDef("总浮盈%", FT_NUMBER),
        FieldDef("当日盈亏", FT_NUMBER),
        FieldDef("持仓只数", FT_NUMBER),
    ]


def _list_fields(client, table_id):
    url = f"{client.BASE_URL}/bitable/v1/apps/{client.base_app_token}/tables/{table_id}/fields"
    out = []
    page_token = None
    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token
        resp = requests.get(url, headers=client._headers(), params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"list_fields error: {data}")
        out.extend(data["data"]["items"])
        if not data["data"].get("has_more"):
            break
        page_token = data["data"].get("page_token")
    return out


def _create_field(client, table_id, name, ftype, property=None):
    url = f"{client.BASE_URL}/bitable/v1/apps/{client.base_app_token}/tables/{table_id}/fields"
    body = {"field_name": name, "type": ftype}
    if property:
        body["property"] = property
    resp = requests.post(url, headers=client._headers(), json=body, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"create_field {name} error: {data}")


def _update_field(client, table_id, field_id, name, ftype):
    url = f"{client.BASE_URL}/bitable/v1/apps/{client.base_app_token}/tables/{table_id}/fields/{field_id}"
    body = {"field_name": name, "type": ftype}
    resp = requests.put(url, headers=client._headers(), json=body, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"update_field {field_id} error: {data}")


def sync_table(client, table_id: str, label: str, schema: list[FieldDef]) -> None:
    print(f"\n--- Syncing {label} ({table_id}) ---")
    existing = _list_fields(client, table_id)
    existing_names = {f["field_name"] for f in existing}

    if schema and existing and schema[0].name not in existing_names:
        first_existing = existing[0]
        try:
            _update_field(
                client,
                table_id,
                first_existing["field_id"],
                schema[0].name,
                first_existing["type"],
            )
            print(f"~ renamed default field '{first_existing['field_name']}' -> '{schema[0].name}'")
        except (RuntimeError, requests.HTTPError) as e:
            print(f"! rename default field failed: {e}")
        existing = _list_fields(client, table_id)
        existing_names = {f["field_name"] for f in existing}

    for fdef in schema:
        if fdef.name in existing_names:
            print(f"= '{fdef.name}' exists, skipping")
            continue
        try:
            _create_field(client, table_id, fdef.name, fdef.type, fdef.property)
            print(f"+ '{fdef.name}' created")
        except (RuntimeError, requests.HTTPError) as e:
            print(f"! '{fdef.name}' failed: {e}")


def main():
    load_dotenv()
    client = BitableClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
        os.environ["FEISHU_BASE_APP_TOKEN"],
    )

    tables = {
        "sectors": os.environ["TABLE_ID_SECTORS"],
        "tickers": os.environ["TABLE_ID_TICKERS"],
        "indicators": os.environ["TABLE_ID_INDICATORS"],
        "price_snapshots": os.environ["TABLE_ID_PRICE_SNAPSHOTS"],
        "sector_news": os.environ["TABLE_ID_SECTOR_NEWS"],
        "decisions": os.environ["TABLE_ID_DECISIONS"],
        "trading_rules": os.environ["TABLE_ID_TRADING_RULES"],
        "trades": os.environ["TABLE_ID_TRADES"],
        "portfolio": os.environ["TABLE_ID_PORTFOLIO"],
        "asset_snapshots": os.environ["TABLE_ID_ASSET_SNAPSHOTS"],
    }

    # Order matters: 板块表 must exist before tables that link to it
    sync_table(client, tables["sectors"], "板块表", schema_for_sectors())
    sync_table(client, tables["tickers"], "标的表", schema_for_tickers(tables["sectors"]))
    sync_table(client, tables["indicators"], "指标表", schema_for_indicators())
    sync_table(client, tables["price_snapshots"], "行情快照表", schema_for_price_snapshots())
    sync_table(client, tables["sector_news"], "板块新闻表", schema_for_sector_news(tables["sectors"]))
    sync_table(client, tables["decisions"], "决策记录表", schema_for_decisions())
    sync_table(client, tables["trading_rules"], "交易纪律表", schema_for_trading_rules())
    sync_table(client, tables["trades"], "交易记录表", schema_for_trades())
    sync_table(client, tables["portfolio"], "持仓表", schema_for_portfolio(tables["sectors"]))
    sync_table(client, tables["asset_snapshots"], "资产快照表", schema_for_asset_snapshots())

    print("\n✅ Schema sync complete.")


if __name__ == "__main__":
    main()
