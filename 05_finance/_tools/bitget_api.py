#!/usr/bin/env python3
"""Bitget v2 API 只读客户端：纯标准库。端点定义集中于此（UTA 升级时只改这里）。
密钥从 ~/.config/lifeos/bitget.env 读（chmod 600，永不进 git），格式：
BITGET_API_KEY=... / BITGET_API_SECRET=... / BITGET_PASSPHRASE=...
对话与日志不得出现明文。"""
import base64, hmac, hashlib, json, os, time, urllib.request, urllib.parse

BASE = "https://api.bitget.com"
ENV_PATH = os.path.expanduser("~/.config/lifeos/bitget.env")

def prehash(ts, method, path, query="", body=""):
    q = f"?{query}" if query else ""
    return f"{ts}{method.upper()}{path}{q}{body}"

def sign(secret, prehash_str):
    return base64.b64encode(hmac.new(secret.encode(), prehash_str.encode(), hashlib.sha256).digest()).decode()

def load_credentials(path=ENV_PATH):
    if not os.path.exists(path):
        return None
    creds = {}
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            creds[k.strip()] = v.strip()
    need = ("BITGET_API_KEY", "BITGET_API_SECRET", "BITGET_PASSPHRASE")
    return creds if all(creds.get(k) for k in need) else None

def request(path, params=None, creds=None, retries=1):
    creds = creds or load_credentials()
    if creds is None:
        raise RuntimeError(f"缺少密钥文件 {ENV_PATH}（chmod 600，三行 KEY/SECRET/PASSPHRASE）")
    query = urllib.parse.urlencode(sorted((params or {}).items()))
    ts = str(int(time.time() * 1000))
    sig = sign(creds["BITGET_API_SECRET"], prehash(ts, "GET", path, query))
    url = f"{BASE}{path}" + (f"?{query}" if query else "")
    req = urllib.request.Request(url, headers={
        "ACCESS-KEY": creds["BITGET_API_KEY"], "ACCESS-SIGN": sig,
        "ACCESS-TIMESTAMP": ts, "ACCESS-PASSPHRASE": creds["BITGET_PASSPHRASE"],
        "Content-Type": "application/json", "locale": "zh-CN"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            if data.get("code") != "00000":
                raise RuntimeError(f"Bitget API 错误 code={data.get('code')} msg={data.get('msg')}")
            return data["data"]
        except Exception:
            if attempt >= retries:
                raise
            time.sleep(2)

def all_account_balance():
    return request("/api/v2/account/all-account-balance")

def history_position(start_ms=None, end_ms=None, id_less_than=None):
    p = {"productType": "USDT-FUTURES", "limit": "100"}
    if start_ms: p["startTime"] = str(start_ms)
    if end_ms: p["endTime"] = str(end_ms)
    if id_less_than: p["idLessThan"] = str(id_less_than)   # 游标分页（endId 续页）
    return request("/api/v2/mix/position/history-position", p)

def futures_accounts():
    return request("/api/v2/mix/account/accounts", {"productType": "USDT-FUTURES"})

def fills(start_ms=None, end_ms=None):
    p = {"productType": "USDT-FUTURES", "limit": "100"}
    if start_ms: p["startTime"] = str(start_ms)
    if end_ms: p["endTime"] = str(end_ms)
    return request("/api/v2/mix/order/fills", p)
