import unittest, sys, os, csv, tempfile, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
FIX = os.path.join(HERE, "fixtures", "bitget_closedpnl_sample.csv")

def run_cli(args):
    return subprocess.run([sys.executable, os.path.join(TOOLS, "import_closed_pnl.py")] + args,
                          capture_output=True, text=True)

class TestImportCli(unittest.TestCase):
    def setUp(self):
        self.store = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False); self.store.close()
        os.unlink(self.store.name)          # CLI 需自建含表头的文件
        self.addCleanup(lambda: os.path.exists(self.store.name) and os.unlink(self.store.name))

    def test_first_import_appends_all(self):
        r = run_cli([FIX, "--store", self.store.name])
        rep = json.loads(r.stdout)
        self.assertEqual(rep["added"], 4); self.assertEqual(rep["skipped"], 0)
        rows = list(csv.DictReader(open(self.store.name)))
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r2["setup"] == "unlabeled" for r2 in rows))

    def test_replay_same_file_skips_silently(self):
        run_cli([FIX, "--store", self.store.name])
        rep = json.loads(run_cli([FIX, "--store", self.store.name]).stdout)
        self.assertEqual(rep["added"], 0); self.assertEqual(rep["skipped"], 4)
        self.assertEqual(rep["suspected"], 0)   # 同 source_file 重放豁免

    def test_same_hash_other_file_suspected(self):
        run_cli([FIX, "--store", self.store.name])
        import shutil; dup = FIX.replace("sample", "sample_copy"); shutil.copy(FIX, dup)
        self.addCleanup(os.unlink, dup)
        rep = json.loads(run_cli([dup, "--store", self.store.name]).stdout)
        self.assertEqual(rep["added"], 0); self.assertEqual(rep["suspected"], 4)   # 不静默删、不入库，待人工确认

    def test_zero_byte_store_gets_header(self):
        # 存量文件存在但 0 字节：append 必须先补表头，否则首行数据被当表头 → 账本损坏
        open(self.store.name, "w").close()
        rep = json.loads(run_cli([FIX, "--store", self.store.name]).stdout)
        self.assertEqual(rep["added"], 4)
        with open(self.store.name, encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            self.assertIn("close_time", reader.fieldnames)
            self.assertIn("setup", reader.fieldnames)
            rows = list(reader)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["row_hash"] for r in rows))
