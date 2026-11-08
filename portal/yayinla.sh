#!/usr/bin/env bash
# Siteyi, portalı ve dokümantasyonu VDS'e yükler ve hizmeti yeniden başlatır (yalnızca kod/site; veritabanına dokunmaz).
#   bash portal/yayinla.sh            # ssh takma adı: vds
set -euo pipefail
HEDEF="${1:-vds}"
KOK="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KOK/site" && (py -3 build.py 2>/dev/null || python3 build.py)
cd "$KOK/belgeler" && (py -3 build.py 2>/dev/null || python3 build.py)
cd "$KOK"
MODULLER="portal gorsel sosyal hesap eposta api api_sema"
DOSYALAR=""
for d in $MODULLER; do DOSYALAR="$DOSYALAR portal/$d.py"; done
tar --exclude='__pycache__' --exclude='*.pyc' --exclude='site/TASARIM.md' \
    -czf - site belgeler/cikti $DOSYALAR | ssh "$HEDEF" "
  set -e
  mkdir -p /opt/modelen/yeni && rm -rf /opt/modelen/yeni/* && tar -xzf - -C /opt/modelen/yeni
  rm -rf /opt/modelen/site.eski && [ -d /opt/modelen/site ] && mv /opt/modelen/site /opt/modelen/site.eski || true
  mv /opt/modelen/yeni/site /opt/modelen/site
  rm -rf /opt/modelen/belgeler.eski && [ -d /opt/modelen/belgeler ] && mv /opt/modelen/belgeler /opt/modelen/belgeler.eski || true
  mv /opt/modelen/yeni/belgeler/cikti /opt/modelen/belgeler
  mkdir -p /opt/modelen/portal
  for d in $MODULLER; do mv /opt/modelen/yeni/portal/\$d.py /opt/modelen/portal/\$d.py; done
  chown -R root:modelen /opt/modelen/site /opt/modelen/portal && chmod -R g+rX,o-rwx /opt/modelen/site /opt/modelen/portal
  chown -R root:root /opt/modelen/belgeler && chmod -R a+rX /opt/modelen/belgeler
  rm -rf /opt/modelen/yeni /opt/modelen/site.eski /opt/modelen/belgeler.eski
  systemctl restart modelen-portal && sleep 1 && systemctl is-active modelen-portal
"
echo "Yayınlandı: https://modelen.tr  ve dokümantasyon dosyaları /opt/modelen/belgeler (docs.modelen.tr için Caddy bloğu gerekir)"
