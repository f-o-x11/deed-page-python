import os, stat, tempfile, unittest
from pathlib import Path

class T(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["XDG_CONFIG_HOME"] = str(self.tmp / "cfg")
        os.environ.pop("DEED_PAGE_TOKEN", None); os.environ.pop("DEEDPAGE_TOKEN", None)

    def test_collect_and_token(self):
        import deed_page as dp
        s = self.tmp / "site"; (s / "css").mkdir(parents=True)
        (s / "index.html").write_text("<h1>x</h1>"); (s / "css/a.css").write_text("h1{}")
        (s / "logo.png").write_bytes(b"\x89PNG")
        m = dp.collect_files(s)
        self.assertEqual(m["index.html"], "<h1>x</h1>"); self.assertEqual(m["css/a.css"], "h1{}")
        self.assertEqual(m["logo.png"], {"base64": "iVBORw=="})
        self.assertEqual(list(dp.collect_files(s / "index.html")), ["index.html"])
        self.assertIsNone(dp.load_token())
        p = dp.save_token("deed_tok_test123")
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)
        self.assertEqual(dp.load_token(), "deed_tok_test123")
        os.environ["DEED_PAGE_TOKEN"] = "deed_tok_env"; self.assertEqual(dp.load_token(), "deed_tok_env")
        self.assertEqual(dp.redact({"token": "deed_tok_a-1"}), {"token": "<redacted>"})

if __name__ == "__main__":
    unittest.main()
