import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bitget_api import sign, prehash

class TestSign(unittest.TestCase):
    def test_prehash_get_with_query(self):
        self.assertEqual(
            prehash("1700000000000", "GET", "/api/v2/mix/position/history-position",
                    query="endTime=2&startTime=1", body=""),
            "1700000000000GET/api/v2/mix/position/history-position?endTime=2&startTime=1")

    def test_prehash_no_query_no_body(self):
        self.assertEqual(prehash("1", "GET", "/p", query="", body=""), "1GET/p")

    def test_sign_known_vector(self):
        # 自算向量（实算，非占位）：
        # python3 -c "import hmac,hashlib,base64;print(base64.b64encode(hmac.new(b'secret',b'1GET/p',hashlib.sha256).digest()).decode())"
        self.assertEqual(sign("secret", "1GET/p"), "qvZZcezy2j6MA53ZsLxZCv3/9ZX1rQoHK++RYnwv7I0=")

class TestEnv(unittest.TestCase):
    def test_load_env_missing_returns_none(self):
        from bitget_api import load_credentials
        self.assertIsNone(load_credentials("/nonexistent/path.env"))


class TestFuturesAccounts(unittest.TestCase):
    """1.6 设计 §2 第 4 个端点封装：futures_accounts（USDT-FUTURES 账户权益）。
    离线测试：只验证封装存在 + 无密钥守卫，不发网络请求。"""

    def test_exists_and_callable(self):
        import bitget_api
        self.assertTrue(callable(getattr(bitget_api, "futures_accounts", None)))

    def test_no_credentials_raises_runtimeerror_with_env_path(self):
        # mock 掉 load_credentials（不依赖本机是否存在真实 env 文件），
        # 走 request() 的无密钥守卫，提前抛错 → 不触网。
        import bitget_api
        from unittest.mock import patch
        with patch("bitget_api.load_credentials", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                bitget_api.futures_accounts()
        self.assertIn(bitget_api.ENV_PATH, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
