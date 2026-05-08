"""Ad-hoc: swap mis-entered columns in 交易纪律表.

User filled data shifted by one column. This script reads each rule, detects
whether 类型 / 优先级 / 详细描述 are mis-mapped (类型 holding a value from
{必守,重要,参考} confirms the shift), and rewrites with corrected values.
"""

import os

from dotenv import load_dotenv

from scripts.bitable_client import BitableClient


PRIORITY_VALUES = {"必守", "重要", "参考"}
TYPE_VALUES = {"仓位管理", "进场", "止损", "止盈", "心态"}


def _text(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in v).strip()
    return str(v).strip()


def main():
    load_dotenv()
    c = BitableClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
        os.environ["FEISHU_BASE_APP_TOKEN"],
    )
    table_id = os.environ["TABLE_ID_TRADING_RULES"]
    rules = c.list_records(table_id)

    fixed = 0
    skipped = 0
    for r in rules:
        rid = r["record_id"]
        f = r.get("fields", {})
        title = _text(f.get("纪律标题"))
        cur_type = _text(f.get("类型"))
        cur_priority = _text(f.get("优先级"))
        cur_desc = _text(f.get("详细描述"))

        # Detect shift: 类型 holds a 优先级 value AND 详细描述 holds a 类型 value
        if cur_type in PRIORITY_VALUES and cur_desc in TYPE_VALUES:
            new_fields = {
                "类型": cur_desc,        # was in 详细描述
                "优先级": cur_type,      # was in 类型
                "详细描述": cur_priority,  # was in 优先级
            }
            print(f"FIX {title!r}:")
            print(f"  类型: {cur_type!r} -> {new_fields['类型']!r}")
            print(f"  优先级: {cur_priority[:30]!r}... -> {new_fields['优先级']!r}")
            print(f"  详细描述: {cur_desc!r} -> {new_fields['详细描述'][:30]!r}...")
            c.update_record(table_id, rid, new_fields)
            fixed += 1
        else:
            print(f"SKIP {title!r} (already correct or unrecognized pattern)")
            skipped += 1

    print(f"\nFixed {fixed}, skipped {skipped}")


if __name__ == "__main__":
    main()
