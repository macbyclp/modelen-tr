#!/bin/sh
# Gunluk veritabani yedegi (sqlite .backup, tutarli); 14 gun saklanir
set -e
/usr/bin/python3 - <<'PY'
import sqlite3, time
src = sqlite3.connect("/opt/modelen/veri/portal.db")
dst = sqlite3.connect("/opt/modelen/yedek/portal-" + time.strftime("%Y%m%d-%H%M") + ".db")
src.backup(dst); dst.close(); src.close()
PY
find /opt/modelen/yedek -name "portal-*.db" -mtime +14 -delete
