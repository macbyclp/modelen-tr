"""Dokümantasyon sitesi testi: derleme başarılı mı, iç bağlantılar çözülüyor mu."""
import os, re, subprocess, sys, unittest
from html.parser import HTMLParser

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KOK, "cikti")


class Toplayici(HTMLParser):
    def __init__(self):
        super().__init__()
        self.linkler, self.idler = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.linkler.append(a["href"])
        if a.get("id"):
            self.idler.add(a["id"])


def sayfa_yolu(url):
    yol = url.split("#")[0].split("?")[0]
    if not yol:
        return None
    p = os.path.join(CIKTI, yol.lstrip("/"))
    if os.path.isdir(p) or yol.endswith("/"):
        p = os.path.join(p, "index.html")
    return p


class Belgeler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = subprocess.run([sys.executable, os.path.join(KOK, "build.py")], capture_output=True)
        assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
        cls.sayfalar = {}
        for d, _, fs in os.walk(CIKTI):
            for f in fs:
                if f.endswith(".html"):
                    p = os.path.join(d, f)
                    t = Toplayici()
                    t.feed(open(p, encoding="utf-8").read())
                    cls.sayfalar[p] = t

    def test_ic_baglantilar_cozuluyor(self):
        eksik = []
        for p, t in self.sayfalar.items():
            for h in t.linkler:
                if re.match(r"^(https?:|mailto:|data:|javascript:)", h):
                    continue
                if h.startswith("#"):
                    if h[1:] and h[1:] not in t.idler:
                        eksik.append((os.path.relpath(p, CIKTI), h))
                    continue
                hedef = sayfa_yolu(h)
                if hedef is None:
                    continue
                if not os.path.exists(hedef):
                    eksik.append((os.path.relpath(p, CIKTI), h))
                elif "#" in h and hedef in self.sayfalar:
                    cap = h.split("#", 1)[1]
                    if cap and cap not in self.sayfalar[hedef].idler:
                        eksik.append((os.path.relpath(p, CIKTI), h))
        self.assertEqual(eksik, [])

    def test_temel_dosyalar(self):
        for f in ("index.html", "openapi.json", "sitemap.xml", "robots.txt", "404.html", "en/index.html"):
            self.assertTrue(os.path.exists(os.path.join(CIKTI, f)), f)


if __name__ == "__main__":
    unittest.main()
