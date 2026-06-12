#!/usr/bin/env python3
"""Bitget API 拉取 → 归一化为内部 schema（与 load_bitget_csv 同构），
经 LOADERS 注册表进 import_closed_pnl.py 同一 dedup/append 管道。
归一化是离线纯函数（TDD）；fetch_closed_pnl 实调网络，仅 Task N 烟雾测试后启用。

⚠️ pnl 映射未锁定：realized_pnl 暂取 API `pnl` 字段（毛口径候选），
`pnl`/`netProfit` ↔ CSV「仓位盈亏/已实现盈亏」的精确对应须经 Task N
用 W23 已落盘 9 行与 API 同窗口逐行对账后修订（见 exchange-schemas.md API 段）。"""
from datetime import datetime, timezone, timedelta

import bitget_api
import parse_trades

_TZ_UTC8 = timezone(timedelta(hours=8))   # 固定 UTC+8，与 CSV 同口径，不依赖本机时区

SOURCE_FILE = "api:history-position"

def normalize_history_position(item):
    """history-position 单条 → 内部 schema 字符串记录（risk/_schema.md §2）。
    - close_time：uTime 毫秒 → 'YYYY-MM-DD HH:MM:SS'（固定 UTC+8）
    - fee = −(totalFunding+openFee+closeFee)，经 _fmt_num 规范化（同 CSV 折叠公式）
    - realized_pnl 暂= pnl —— 映射未锁定，须经 Task N 实测对账后修订；
      pnl_raw / net_profit_raw 两候选原样保留供对账（writer 按 STORE_FIELDS 过滤，不落盘）
    - source_id = positionId（去重主键激活）；row_hash 仍计算（CSV 兜底路径互见）
    - setup 不在此设置，由 CLI 层 setdefault（同 CSV 路径）"""
    ms = int(item["uTime"])
    rec = {
        "close_time": datetime.fromtimestamp(ms / 1000, tz=_TZ_UTC8).strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": item["symbol"].strip(),
        "direction": item["holdSide"].strip().lower(),
        "open_avg": item["openAvgPrice"].strip(),
        "close_avg": item["closeAvgPrice"].strip(),
        "qty": item["closeTotalPos"].strip(),
        "realized_pnl": item["pnl"].strip(),
        "fee": parse_trades._fmt_num(-(float(item["totalFunding"]) +
                                       float(item["openFee"]) +
                                       float(item["closeFee"]))),
        "pnl_raw": item["pnl"].strip(),
        "net_profit_raw": item["netProfit"].strip(),
        "source_id": item["positionId"].strip(),
        "exchange": "bitget",
        "market_type": "futures",
        "source_file": SOURCE_FILE,
    }
    rec["row_hash"] = parse_trades.closed_row_hash(rec)
    return rec

def fetch_closed_pnl(start_ms=None, end_ms=None):
    """拉取窗口内全部已平仓回合（游标分页 endId+idLessThan，每页 ≤100）→ 归一化列表。
    实调网络——测试不调用；3 个月回溯窗口约束见 exchange-schemas.md API 段。"""
    rows, cursor = [], None
    while True:
        data = bitget_api.history_position(start_ms, end_ms, id_less_than=cursor)
        items = (data or {}).get("list") or []
        rows.extend(normalize_history_position(it) for it in items)
        end_id = (data or {}).get("endId")
        if not end_id or len(items) < 100:
            break
        cursor = end_id
    return rows

def load_api_closed_pnl(path_ignored="", kind="closed_pnl_api", start_ms=None, end_ms=None):
    """LOADERS 适配器：签名兼容 loader 约定 (path, kind=...)→(rows, warnings)。
    path 对 API 轨道无意义、忽略；窗口参数由 CLI 层（Task O --since）换算传入。"""
    if kind != "closed_pnl_api":
        raise ValueError(f"unsupported kind: {kind!r}")
    return fetch_closed_pnl(start_ms, end_ms), []
