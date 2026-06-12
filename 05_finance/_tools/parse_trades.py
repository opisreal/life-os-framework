import csv
import hashlib
import io
import os
import re

# 新交易所接入 = 新 load_<ex>_csv / fetch 归一化函数，输出满足 risk/_schema.md 内部字段契约
LOADERS = {                              # 值为本模块函数名，由 CLI getattr(parse_trades, …) 分发
    ("bitget", "closed_pnl"): "load_bitget_csv",
    ("bitget", "closed_pnl_api"): "load_api_closed_pnl",   # 实现在 fetch_bitget，经下方转发 stub
}

def load_api_closed_pnl(path_ignored="", kind="closed_pnl_api", **kw):
    """转发 stub → fetch_bitget.load_api_closed_pnl。实现放 fetch_bitget（网络侧），
    此处保留同名薄转发使 LOADERS 维持「值=本模块函数名」的 getattr 分发契约，
    CSV 路径分发零改动（--source api 接线在 Task O）。惰性 import 避免循环依赖
    （fetch_bitget 反向 import 本模块取 closed_row_hash/_fmt_num）。"""
    import fetch_bitget
    return fetch_bitget.load_api_closed_pnl(path_ignored, kind=kind, **kw)

HASH_FIELDS = ("time", "exchange", "market_type", "symbol", "side",
               "position_side", "price", "base_qty", "fee_amount")

CLOSED_HASH_FIELDS = ("close_time", "exchange", "symbol", "direction",
                      "open_avg", "close_avg", "qty", "realized_pnl")

def row_hash(fill):
    """稳定指纹：仅由成交本质字段派生，用于无 source_id 时去重。"""
    key = "|".join(str(fill.get(f, "")) for f in HASH_FIELDS)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

def closed_row_hash(rec):
    """已平仓回合的稳定指纹（无 source_id 时去重用），sha256[:16]。
    不能复用 fills 的 row_hash：其字段（time/side/price/base_qty…）在
    closed-pnl 记录里大多缺失，同 symbol 所有回合会碰撞。
    字符串稳定性契约：哈希输入是规范化后的字符串值（剥后缀之后、转 float 之前，
    即写入 risk/closed-pnl.csv 的原样字符串），因此重新读回自家 CSV 必产生相同哈希。"""
    key = "|".join(str(rec.get(f, "")) for f in CLOSED_HASH_FIELDS)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

def dedup_closed_rounds(rows):
    """已平仓回合去重，语义同 dedup_fills：有 source_id 同 id 直接去重；
    无 source_id 同 closed_row_hash 标疑似、保留全部交用户确认（不静默删）。
    互盲修复（MVP-1.6 触发）：带 source_id 的行（API 来源）在登记 seen_ids 的
    同时也登记 closed_row_hash 到 seen_hashes——API（有 id）与 CSV（无 id）
    混用时，同一回合的无 id 行会命中该 hash 被标 suspected 交人工确认，
    不再互不可见。
    与 dedup_fills 每次重算哈希不同，本函数显式信任已存在的 r["row_hash"]
    （重读自家落盘 CSV 的行自带哈希，按字符串稳定性契约与重算结果一致），
    缺失时才现算。返回 (kept, suspected)。"""
    kept, suspected = [], []
    seen_ids, seen_hashes = set(), set()
    for r in rows:
        sid = r.get("source_id") or ""
        if sid:
            if sid in seen_ids:
                continue
            seen_ids.add(sid)
            seen_hashes.add(r.get("row_hash") or closed_row_hash(r))
            kept.append(r)
        else:
            h = r.get("row_hash") or closed_row_hash(r)
            kept.append(r)
            if h in seen_hashes:
                suspected.append(r)
            else:
                seen_hashes.add(h)
    return kept, suspected

_NUM_RE = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")

# 合法千分位分组：1,234 / 1,234,567.89（首段 1-3 位，其后每段恰 3 位）
_GROUPED_NUM_RE = re.compile(r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?")

def _strip_suffix(s):
    """剥离数值字符串的尾部单位后缀（'336H'→'336'，'-0.04USDT'→'-0.04'）。
    含逗号时仅接受合法千分位分组（'5,062.5USDT'→'5062.5'）并剔除逗号；
    非法分组（'1,2,9'）或欧式小数逗号（'5.062,5'）整体拒绝返回 None
    （防 magnitude 错误的静默通过）。剥出数字后残尾必须为空串或纯字母单位，
    否则整体拒绝（'5.062.5USDT'→None，上游按 warning 跳行）。
    无前导数值 → 返回 None。"""
    cell = s.strip()
    if "," in cell:
        gm = _GROUPED_NUM_RE.match(cell)
        if not gm:
            return None
        cell = gm.group(0).replace(",", "") + cell[gm.end():]
    m = _NUM_RE.match(cell)
    if not m:
        return None
    if not re.fullmatch(r"[A-Za-z]*", cell[m.end():]):
        return None
    return m.group(0)

_CONTRACT_RE = re.compile(r"^(\S+)\s+(Long|Short)·(Cross|Isolated)$")

def _fmt_num(x):
    """fee 等派生数值的规范字符串：定点 12 位小数去尾零，确定性输出。"""
    s = f"{x:.12f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s

# Bitget 已平仓盈亏（历史仓位导出）原始列名，映射规则见 _import/exchange-schemas.md
_BG_CLOSED_HEADER_KEY = "已实现盈亏"

def load_bitget_csv(path, kind="closed_pnl"):
    """读 Bitget 导出 CSV → (rows, warnings)。
    kind="closed_pnl"：U 本位合约历史仓位导出（列映射见 _import/exchange-schemas.md）。
    - 编码 utf-8-sig 优先，失败兜底 gb18030
    - 表头按内容定位（首个含「已实现盈亏」的行），不假定行号
    - 数值字段保留规范化字符串（剥后缀、不转 float），float 转换交下游
      （compute_pnl_stats 内部 float()）
    - fee = −(资金费用+开仓手续费+平仓手续费)；realized_pnl − fee == 仓位盈亏（净）
    - 逐行校验 |已实现盈亏+资金费用+两手续费−仓位盈亏| < 1e-6，不满足 → 收入
      warnings（行保留，不静默丢）；合约格式无法解析 → 收入 warnings 并跳过该行
    - 平仓量按 symbol 推导的基础资产精确剥后缀（1000PEPEUSDT→1000PEPE），
      不匹配才回退正则剥尾部非数字 + warning
    - 数值单元格为空/--/无法解析 → warning（标行列）并跳过该行，不中断导入；
      表头缺必需列 → 返回 ([], [warning])，不抛 KeyError
    - 导出无唯一 ID → source_id=""，row_hash=closed_row_hash(rec) 作去重指纹"""
    if kind != "closed_pnl":
        raise ValueError(f"unsupported kind: {kind!r}（fills 待校准，见 exchange-schemas.md）")
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gb18030")
    lines = list(csv.reader(io.StringIO(text)))
    header_i = next((i for i, ln in enumerate(lines)
                     if any(_BG_CLOSED_HEADER_KEY in c for c in ln)), None)
    if header_i is None:
        return [], [f"{os.path.basename(path)}: 未找到含「{_BG_CLOSED_HEADER_KEY}」的表头行"]
    header = [c.strip() for c in lines[header_i]]
    col = {name: idx for idx, name in enumerate(header)}
    src = os.path.basename(path)
    required_cols = ("合约", "全部平仓时间", "开仓均价", "平仓均价", "平仓量",
                     "已实现盈亏", "资金费用", "开仓手续费", "平仓手续费", "仓位盈亏")
    missing = [c for c in required_cols if c not in col]
    if missing:
        return [], [f"{src}: 表头缺少必需列：{'、'.join(missing)}，整个文件未导入"]
    rows, warnings = [], []
    for ln_no, cells in enumerate(lines[header_i + 1:], header_i + 2):
        if not cells or all(not c.strip() for c in cells):
            continue
        contract = cells[col["合约"]].strip()
        m = _CONTRACT_RE.match(contract)
        if not m:
            warnings.append(f"{src} 第{ln_no}行: 合约格式无法解析「{contract}」，已跳过")
            continue
        symbol, direction = m.group(1), m.group(2).lower()
        money, bad_cols = {}, []
        for c in ("已实现盈亏", "资金费用", "开仓手续费", "平仓手续费", "仓位盈亏"):
            money[c] = _strip_suffix(cells[col[c]])
            if money[c] is None:
                bad_cols.append(c)
        # 平仓量优先按基础资产精确剥后缀：1000PEPE/10000SATS 等数字前缀资产
        # 用「剥尾部非数字」正则会把资产名前缀吞进数量（350+1000PEPE→3501000）。
        base_asset = symbol[:-4] if symbol.endswith("USDT") and len(symbol) > 4 else symbol
        qty_cell = cells[col["平仓量"]].strip()
        if qty_cell.endswith(base_asset) and _NUM_RE.fullmatch(qty_cell[:-len(base_asset)]):
            qty = qty_cell[:-len(base_asset)]
        else:
            qty = _strip_suffix(qty_cell)
            if qty is not None:
                warnings.append(f"{src} 第{ln_no}行: 平仓量「{qty_cell}」未以基础资产"
                                f"「{base_asset}」结尾，已按正则回退剥离为「{qty}」，请人工核对")
        if qty is None:
            bad_cols.append("平仓量")
        if bad_cols:
            detail = "、".join(f"「{c}」(原值「{cells[col[c]].strip()}」)" for c in bad_cols)
            warnings.append(f"{src} 第{ln_no}行: 数值列无法解析：{detail}，该行已跳过")
            continue
        rec = {
            "close_time": cells[col["全部平仓时间"]].strip(),
            "symbol": symbol,
            "direction": direction,
            "open_avg": cells[col["开仓均价"]].strip(),
            "close_avg": cells[col["平仓均价"]].strip(),
            "qty": qty,
            "realized_pnl": money["已实现盈亏"],
            "fee": _fmt_num(-(float(money["资金费用"]) +
                              float(money["开仓手续费"]) +
                              float(money["平仓手续费"]))),
            "source_id": "",
            "exchange": "bitget",
            "market_type": "futures",
            "source_file": src,
        }
        rec["row_hash"] = closed_row_hash(rec)
        checksum = (float(money["已实现盈亏"]) + float(money["资金费用"]) +
                    float(money["开仓手续费"]) + float(money["平仓手续费"]) -
                    float(money["仓位盈亏"]))
        if abs(checksum) >= 1e-6:
            warnings.append(f"{src} 第{ln_no}行: 校验和不平（差 {checksum:.8f}），行已保留请人工核对")
        rows.append(rec)
    return rows, warnings

def dedup_fills(fills):
    """有 source_id：同 id 视为重复直接去重。无 source_id：同 row_hash 标为疑似重复，
    保留全部、另列 suspected 交用户确认（不静默删）。返回 (kept, suspected)。"""
    kept, suspected = [], []
    seen_ids, seen_hashes = set(), set()
    for f in fills:
        sid = f.get("source_id") or ""
        if sid:
            if sid in seen_ids:
                continue
            seen_ids.add(sid)
            kept.append(f)
        else:
            h = row_hash(f)
            kept.append(f)
            if h in seen_hashes:
                suspected.append(f)
            else:
                seen_hashes.add(h)
    return kept, suspected

def compute_pnl_stats(closed_rounds):
    """从 Bitget 已平仓盈亏报表算胜率/盈亏比/净盈亏。一条记录=一个已平仓回合。
    win=realized_pnl>0。net_pnl=Σrealized_pnl-Σfee。profit_factor=毛盈/毛亏(无亏损则 None)。
    保本回合(pnl==0)计入 rounds/win_rate 分母但不计 wins/losses。"""
    n = len(closed_rounds)
    if n == 0:
        return {"rounds": 0, "wins": 0, "losses": 0, "breakeven": 0,
                "win_rate": None, "profit_factor": None, "net_pnl": 0.0,
                "gross_profit": 0.0, "gross_loss": 0.0}
    wins = losses = 0
    gross_profit = gross_loss = total_fee = total_pnl = 0.0
    for r in closed_rounds:
        pnl = float(r.get("realized_pnl", 0) or 0)
        fee = float(r.get("fee", 0) or 0)
        total_pnl += pnl
        total_fee += fee
        if pnl > 0:
            wins += 1; gross_profit += pnl
        elif pnl < 0:
            losses += 1; gross_loss += -pnl
    return {
        "rounds": n, "wins": wins, "losses": losses,
        "breakeven": n - wins - losses,
        "win_rate": wins / n,
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else None,
        "net_pnl": total_pnl - total_fee,
        "gross_profit": gross_profit, "gross_loss": gross_loss,
    }

def drawdown_from_peak(equity_series):
    """权益序列（按时间序）当前点相对历史峰值的回撤比例。粒度=周末快照。
    注意：这是'账户权益回撤'，不是从成交流水推的'交易序列回撤'。"""
    if len(equity_series) < 2:
        return 0.0
    peak = max(equity_series)
    current = equity_series[-1]
    if peak <= 0:
        return 0.0
    return max(0.0, (peak - current) / peak)

def drawdown_breaches(equity_series, cap):
    return drawdown_from_peak(equity_series) > cap

def weekly_change(equity_series):
    """最近一期环比变化 (curr-prev)/prev，仅展示用；<2 点或 prev<=0 返回 None。"""
    if len(equity_series) < 2:
        return None
    prev, curr = equity_series[-2], equity_series[-1]
    if prev <= 0:
        return None
    return (curr - prev) / prev

_WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")

def load_equity(path):
    """读 equity CSV：校验 week 格式（YYYY-Wnn 两位零填充）、同 week 重复行报错、按 week 升序返回。
    review/import 一律经此函数取序列，不允许各处现读 CSV。"""
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    seen = set()
    for r in rows:
        wk = r.get("week", "")
        if not _WEEK_RE.match(wk):
            raise ValueError(f"week 格式非法: {wk!r}")
        if wk in seen:
            raise ValueError(f"同 week 重复行: {wk}")
        seen.add(wk)
    return sorted(rows, key=lambda r: r["week"])

def pair_spot_rounds(fills):
    """现货 FIFO 配对：买入入栈，卖出按 FIFO 配对算 realized_pnl。
    卖出时若底仓不足（缺成本）→ 标 low_confidence、不产出回合、不计入统计。
    输入守卫：side 大小写不敏感（strip+lower 归一化）；qty<=0 的成交（买/卖）
    与未知 side（非 buy/sell）均标 low_conf 并跳过，不产出回合。
    已知保守行为：底仓不足的超量卖单在被丢弃前会先消耗掉现有 lots（破坏性消耗），
    导致其后本可配对的卖单也变为 low_conf。
    产出回合不含手续费字段，net 口径=毛利；手续费由调用方另行汇总。
    返回 (rounds, low_conf_count)。fills 假定已按 time 升序。"""
    lots = []           # [[price, qty], ...] FIFO 队列
    rounds, low_conf = [], 0
    for f in fills:
        price = float(f["price"]); qty = float(f["base_qty"])
        side = str(f["side"]).strip().lower()
        if qty <= 0:
            low_conf += 1
            continue
        if side == "buy":
            lots.append([price, qty])
        elif side == "sell":
            remaining = qty; cost = 0.0
            while remaining > 1e-12 and lots:
                lot = lots[0]
                take = min(lot[1], remaining)
                cost += take * lot[0]
                lot[1] -= take; remaining -= take
                if lot[1] <= 1e-12:
                    lots.pop(0)
            if remaining > 1e-12:
                low_conf += 1
                continue
            rounds.append({"realized_pnl": qty * price - cost})
        else:
            low_conf += 1
            continue
    return rounds, low_conf
