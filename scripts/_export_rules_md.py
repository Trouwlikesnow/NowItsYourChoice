"""Ad-hoc: export Bitable 交易纪律表 to docs/dify-knowledge/trading_rules.md."""

import os
from pathlib import Path

from dotenv import load_dotenv

from scripts.bitable_client import BitableClient


def _text(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        parts = []
        for b in v:
            if isinstance(b, dict):
                parts.append(b.get("text", ""))
            else:
                parts.append(str(b))
        return "".join(parts).strip()
    return str(v).strip()


def main():
    load_dotenv()
    c = BitableClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
        os.environ["FEISHU_BASE_APP_TOKEN"],
    )
    rules = c.list_records(os.environ["TABLE_ID_TRADING_RULES"])
    print(f"Loaded {len(rules)} rules")

    priority_order = {"必守": 0, "重要": 1, "参考": 2}

    def sort_key(r):
        f = r.get("fields", {})
        p = _text(f.get("优先级")) or "参考"
        return (priority_order.get(p, 99), _text(f.get("纪律标题")))

    rules.sort(key=sort_key)

    blocks = []
    for r in rules:
        f = r.get("fields", {})
        title = _text(f.get("纪律标题"))
        if not title:
            continue
        status = _text(f.get("状态"))
        if status and status != "启用":
            continue
        rule_type = _text(f.get("类型"))
        priority = _text(f.get("优先级"))
        desc = _text(f.get("详细描述"))

        b = [f"## {title}", ""]
        meta = []
        if rule_type:
            meta.append(f"**类型**：{rule_type}")
        if priority:
            meta.append(f"**优先级**：{priority}")
        if meta:
            b.append("  ".join(meta))
            b.append("")
        if desc:
            b.append(desc)
            b.append("")
        blocks.append("\n".join(b).rstrip())

    body = "\n\n---\n\n".join(blocks)
    content = (
        "# 交易纪律\n\n"
        "来源：飞书 Bitable『交易纪律表』，按优先级（必守 > 重要 > 参考）排序，"
        "仅含状态=启用的条目。\n\n---\n\n"
        + body
        + "\n"
    )

    out = Path("docs/dify-knowledge/trading_rules.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"Wrote {out} ({len(content)} chars)")


if __name__ == "__main__":
    main()
