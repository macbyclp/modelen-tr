#!/usr/bin/env bash
# Siteyi ve portalı VDS'e yükler ve hizmeti yeniden başlatır (yalnızca kod/site; veritabanına dokunmaz).
#   bash portal/yayinla.sh            # ssh takma adı: vds
set -euo pipefail
HEDEF="${1:-vds}"
KOK="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KOK/site" && (py -3 build.py 2>/dev/null || python3 build.py)
cd "$KOK"
tar --exclude='__pycache__' --exclude='*.pyc' --exclude='site/TASARIM.md' \
    -czf - site portal/portal.py portal/gorsel.py portal/sosyal.py | ssh "$HEDEF" '
  set -e
  mkdir -p /opt/modelen/yeni && rm -rf /opt/modelen/yeni/* && tar -xzf - -C /opt/modelen/yeni
  rm -rf /opt/modelen/site.eski && [ -d /opt/modelen/site ] && mv /opt/modelen/site /opt/modelen/site.eski || true
  mv /opt/modelen/yeni/site /opt/modelen/site
  mkdir -p /opt/modelen/portal
  for d in portal gorsel sosyal; do mv /opt/modelen/yeni/portal/$d.py /opt/modelen/portal/$d.py; done
  chown -R root:modelen /opt/modelen/site /opt/modelen/portal && chmod -R g+rX,o-rwx /opt/modelen/site /opt/modelen/portal
  rm -rf /opt/modelen/yeni /opt/modelen/site.eski
  systemctl restart modelen-portal && sleep 1 && systemctl is-active modelen-portal
'
echo "Yayınlandı: https://modelen.tr"
