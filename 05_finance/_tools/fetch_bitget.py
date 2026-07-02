#!/usr/bin/env python3
"""Bitget API 拉取 → 归一化为内部 schema（与 load_bitget_csv 同构），
经 LOADERS 注册表进 import_closed_pnl.py 同一 dedup/append 管道。
归一化是离线纯函数（TDD）；fetch_closed_pnl 实调网络，仅 Task N 烟雾测试后启用。

映射已于 2026-06-13 经 9/9 真实对账锁定：pnl→realized_pnl（毛），
netProfit=净（校验和 netProfit==pnl+totalFunding+openFee+closeFee）。
真实返回时间字段为小写 utime/ctime（与官方文档 uTime/cTime 不符），
归一化兼容两种大小写（见 exchange-schemas.md API 段）。"""
from datetime import datetime, timezone, timedelta

import bitget_api
import parse_trades

_TZ_UTC8 = timezone(timedelta(hours=8))   # 固定 UTC+8，与 CSV 同口径，不依赖本机时区

SOURCE_FILE = "api:history-position"

def normalize_history_position(item):
    """history-position 单条 → 内部 schema 字符串记录（risk/_schema.md §2）。
    - close_time：utime 毫秒 → 'YYYY-MM-DD HH:MM:SS'（固定 UTC+8）。
      真实 API 返回小写 utime/ctime；保留 uTime/cTime 大写兜底（文档变体）
    - fee = −(totalFunding+openFee+closeFee)，经 _fmt_num 规范化（同 CSV 折叠公式）
    - realized_pnl = pnl（毛价格盈亏）——映射已于 2026-06-13 经 9/9 真实对账锁定：
      pnl→realized_pnl（毛），netProfit=净（校验和 netProfit==pnl+totalFunding+openFee+closeFee）；
      pnl_raw / net_profit_raw 原样保留供未来审计（writer 按 STORE_FIELDS 过滤，不落盘）
    - source_id = positionId（去重主键激活）；row_hash 仍计算（CSV 兜底路径互见）
    - setup 不在此设置，由 CLI 层 setdefault（同 CSV 路径）"""
    ms = int(item.get("utime") or item["uTime"])
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

# ---------- fills（成交明细）→ trades.csv（2026-07-03 真实样本校准） ----------

FILLS_SOURCE_FILE = "api:fills"

# hedge_mode 下 (tradeSide, side) → position_side；单向持仓推导规则未实测，不猜（校准门）
_POSITION_SIDE = {("open", "buy"): "open_long", ("open", "sell"): "open_short",
                  ("close", "sell"): "close_long", ("close", "buy"): "close_short"}

def normalize_fill(item):
    """fills 单条 → trades.csv 内部 schema（risk/_schema.md §1）。
    - time：cTime 毫秒 → 'YYYY-MM-DD HH:MM:SS.mmm'（固定 UTC+8，含毫秒——
      同秒同价同量的合法重复靠毫秒区分）。真实返回大写 cTime（与 history-position
      的小写 utime/ctime 相反），小写 ctime 兜底
    - fee_amount = −Σ feeDetail[].totalFee（正=成本，同 closed-pnl 折叠口径）；
      feeDetail 混币种整行拒绝（不同单位不可求和）
    - posMode 非 hedge_mode 整行拒绝（position_side 推导规则未实测，交 warning 不猜）
    - source_id = tradeId（唯一主键）；row_hash 用 parse_trades.row_hash（fills 字段集）"""
    mode = (item.get("posMode") or "").strip()
    if mode != "hedge_mode":
        raise ValueError(f"fill {item.get('tradeId')}: posMode={mode!r} 未校准（仅 hedge_mode），跳行")
    trade_side = (item.get("tradeSide") or "").strip().lower()
    side = (item.get("side") or "").strip().lower()
    pos = _POSITION_SIDE.get((trade_side, side))
    if pos is None:
        raise ValueError(f"fill {item.get('tradeId')}: (tradeSide={trade_side!r}, side={side!r}) 组合未校准，跳行")
    fee_detail = item.get("feeDetail") or []
    coins = {(f.get("feeCoin") or "").strip() for f in fee_detail}
    if len(coins) > 1:
        raise ValueError(f"fill {item.get('tradeId')}: feeDetail 混币种 {sorted(coins)}，不可求和，跳行")
    fee_total = sum(float(f.get("totalFee") or 0) for f in fee_detail)
    ms = int(item.get("cTime") or item["ctime"])
    dt = datetime.fromtimestamp(ms / 1000, tz=_TZ_UTC8)
    rec = {
        "time": dt.strftime("%Y-%m-%d %H:%M:%S") + f".{ms % 1000:03d}",
        "exchange": "bitget",
        "market_type": "futures",
        "symbol": item["symbol"].strip(),
        "side": side,
        "position_side": pos,
        "price": item["price"].strip(),
        "base_qty": item["baseVolume"].strip(),
        "quote_qty": item["quoteVolume"].strip(),
        "fee_amount": parse_trades._fmt_num(-fee_total),
        "fee_asset": next(iter(coins), ""),
        "source_id": item["tradeId"].strip(),
        "source_file": FILLS_SOURCE_FILE,
    }
    rec["row_hash"] = parse_trades.row_hash(rec)
    return rec

def fetch_fills(start_ms=None, end_ms=None):
    """拉取窗口内全部成交明细（游标分页 endId+idLessThan，每页 ≤100）→ (rows, warnings)。
    单条归一化失败不炸整拉：跳行 + warning（含 tradeId 可溯源）。实调网络——测试不调用。"""
    rows, warnings, cursor = [], [], None
    while True:
        data = bitget_api.fills(start_ms, end_ms, id_less_than=cursor)
        items = (data or {}).get("fillList") or []
        for it in items:
            try:
                rows.append(normalize_fill(it))
            except (ValueError, KeyError) as e:
                warnings.append(str(e))
        end_id = (data or {}).get("endId")
        if not end_id or len(items) < 100:
            break
        cursor = end_id
    return rows, warnings

def load_api_fills(path_ignored="", kind="fills_api", start_ms=None, end_ms=None):
    """LOADERS 适配器（同 load_api_closed_pnl 约定）：(path, kind=...) → (rows, warnings)。"""
    if kind != "fills_api":
        raise ValueError(f"unsupported kind: {kind!r}")
    return fetch_fills(start_ms, end_ms)
