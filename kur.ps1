<#
.SYNOPSIS
  Modelen gönüllü kurulumu (Windows): uygulama + eğitim ortamı + taban model.

.DESCRIPTION
  %LOCALAPPDATA%\Modelen altına kurar:
    modelen.exe, istemci\ (işçi betikleri), .venv\ (Python + PyTorch), models\qwen3-0.6b-base\ (Apache-2.0 taban model).
  Uygulama bu düzeni kendiliğinden bulur (istemci\isci.py ve .venv\Scripts\python.exe).
  Yönetici yetkisi gerekmez. Sistem Python'unu değiştirmez; her şey tek klasördedir. Kaldırmak için klasörü silmeniz yeter.

  Gereksinim: NVIDIA GPU (en az 6 GB VRAM önerilir; 8 GB ile denendi), güncel NVIDIA sürücüsü, ~8 GB boş disk, internet.

.PARAMETER Hedef
  Kurulum klasörü (varsayılan %LOCALAPPDATA%\Modelen).
.PARAMETER Surum
  GitHub sürüm etiketi (varsayılan: en son). Örn. v0.5.0
.PARAMETER Kaynak
  Çevrimdışı/yerel kurulum: modelen.exe ve istemci\ klasörünü içeren dizin (depo kökü). Verilirse GitHub'dan indirilmez.
.PARAMETER CudaSurumu
  PyTorch tekeri: cu124 (varsayılan), cu121, cu126 ya da cpu (yalnızca deneme; eğitim GPU gerektirir).
.PARAMETER ModelAtla
  Taban modeli indirme (yerelde zaten varsa).
.PARAMETER Dene
  Hiçbir şey kurmadan yalnızca ön koşulları denetle ve planı yazdır.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File kur.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File kur.ps1 -Dene
#>
[CmdletBinding()]
param(
  [string]$Hedef = (Join-Path $env:LOCALAPPDATA "Modelen"),
  [string]$Surum = "latest",
  [string]$Kaynak = "",
  [ValidateSet("cu124", "cu121", "cu126", "cpu")][string]$CudaSurumu = "cu124",
  [switch]$ModelAtla,
  [switch]$Dene
)
# Yerel komutlar (uv, python) ilerleme çıktısını stderr'e yazar; Windows PowerShell 5.1'de "Stop" bunu hata sayıp betiği keser.
# Bu yüzden yerel komutlar için "Continue" (çıkış kodunu $LASTEXITCODE ile elle denetleriz), cmdlet'ler için "Stop" kullanılır.
$ErrorActionPreference = "Continue"
$PSDefaultParameterValues["*:ErrorAction"] = "Stop"
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
$ProgressPreference = "SilentlyContinue"   # Invoke-WebRequest çok daha hızlı olur
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$DEPO = "macbyclp/modelen-tr"
$MODEL = "Qwen/Qwen3-0.6B-Base"
$PAKETLER = @("transformers", "peft", "safetensors", "huggingface_hub")
$UV_URL = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"

function Adim($m) { Write-Host "`n==> $m" -ForegroundColor Red }
function Tamam($m) { Write-Host "    $m" -ForegroundColor Gray }
function Hata($m) { Write-Host "`nHATA: $m" -ForegroundColor Yellow; exit 1 }

# ---------------------------------------------------------------- ön koşullar
Adim "Ön koşullar"
if (-not [Environment]::Is64BitOperatingSystem) { Hata "64 bit Windows gerekli." }
$disk = Get-PSDrive -Name ($Hedef.Substring(0, 1)) -ErrorAction SilentlyContinue
if ($disk -and ($disk.Free / 1GB) -lt 8) { Hata ("{0}: sürücüsünde en az 8 GB boş yer gerekli (şu an {1:N1} GB)." -f $Hedef.Substring(0, 1), ($disk.Free / 1GB)) }
Tamam ("Boş disk: {0:N1} GB" -f ($disk.Free / 1GB))
$gpu = $null
try { $gpu = (& nvidia-smi "--query-gpu=name,memory.total" "--format=csv,noheader" 2>$null) | Select-Object -First 1 } catch {}
if ($gpu) {
  Tamam "GPU: $gpu"
  # PyTorch CUDA tekerleri asgari sürücü ister (Windows): cu124 >= 551, cu126 >= 560, cu121 >= 531. Daha eskiyse eğitim başlamaz.
  $asgari = @{ "cu124" = 551; "cu126" = 560; "cu121" = 531 }[$CudaSurumu]
  try {
    $sur = [double](((& nvidia-smi "--query-gpu=driver_version" "--format=csv,noheader" 2>$null) | Select-Object -First 1).Trim().Split(".")[0])
    if ($asgari -and $sur -lt $asgari) {
      Hata ("NVIDIA sürücünüz ({0}) PyTorch {1} için çok eski (en az {2} gerekir). https://www.nvidia.com/drivers adresinden güncelleyin ya da -CudaSurumu cu121 deneyin." -f $sur, $CudaSurumu, $asgari)
    }
  } catch { }
}
elseif ($CudaSurumu -ne "cpu") {
  Hata "NVIDIA GPU ya da sürücüsü bulunamadı (nvidia-smi çalışmıyor). Eğitim NVIDIA GPU gerektirir. Sürücüyü https://www.nvidia.com/drivers adresinden kurup yeniden deneyin; yalnızca denemek için -CudaSurumu cpu kullanabilirsiniz."
}

# PyTorch (Windows) Microsoft Visual C++ çalışma zamanı ister; temiz bir Windows'ta olmayabilir.
if (-not ((Test-Path (Join-Path $env:SystemRoot "System32\vcruntime140.dll")) -and (Test-Path (Join-Path $env:SystemRoot "System32\msvcp140.dll")))) {
  Write-Host "    Visual C++ çalışma zamanı eksik; Microsoft'tan indirilip kuruluyor (yönetici izni isteyebilir)." -ForegroundColor Yellow
  if ($Dene) { Tamam "(-Dene: kurulmadı)" }
  else {
    $vc = Join-Path $env:TEMP "vc_redist.x64.exe"
    Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vc_redist.x64.exe" -OutFile $vc
    $p = Start-Process -FilePath $vc -ArgumentList "/install", "/quiet", "/norestart" -Verb RunAs -Wait -PassThru
    if ($p.ExitCode -notin 0, 1638, 3010) { Hata "Visual C++ çalışma zamanı kurulamadı (kod $($p.ExitCode)). https://aka.ms/vs/17/release/vc_redist.x64.exe adresinden elle kurup yeniden deneyin." }
    Tamam "Visual C++ çalışma zamanı kuruldu"
  }
}
Tamam "Hedef: $Hedef"

if ($Dene) {
  Adim "Plan (-Dene: hiçbir şey kurulmadı)"
  Tamam "1. uv indirilir ($UV_URL)"
  Tamam "2. Python 3.12 sanal ortamı: $Hedef\.venv"
  Tamam "3. PyTorch ($CudaSurumu) + $($PAKETLER -join ', ')"
  $kaynakMetni = if ($Kaynak) { "yerel: $Kaynak" } else { "GitHub $DEPO ($Surum)" }
  Tamam "4. Uygulama ve istemci betikleri: $kaynakMetni"
  Tamam "5. Taban model: $MODEL -> $Hedef\models\qwen3-0.6b-base"
  exit 0
}

New-Item -ItemType Directory -Force -Path $Hedef | Out-Null
$gecici = Join-Path $env:TEMP ("modelen-kur-" + [Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force -Path $gecici | Out-Null

try {
  # ---------------------------------------------------------------- uygulama + betikler
  Adim "Uygulama ve eğitim betikleri"
  if ($Kaynak) {
    if (-not (Test-Path (Join-Path $Kaynak "istemci\isci.py"))) { Hata "$Kaynak içinde istemci\isci.py yok." }
    $exe = @((Join-Path $Kaynak "modelen.exe"), (Join-Path $Kaynak "uygulama\target\release\modelen.exe")) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($exe) { Copy-Item $exe (Join-Path $Hedef "modelen.exe") -Force } else { Write-Host "    UYARI: modelen.exe bulunamadı, yalnızca betikler kuruldu." -ForegroundColor Yellow }
    foreach ($d in @("istemci", "sunucu")) {
      if (Test-Path (Join-Path $Kaynak $d)) {
        Copy-Item (Join-Path $Kaynak $d) $Hedef -Recurse -Force -Exclude "__pycache__", "calisma", "*.pyc"
      }
    }
    Tamam "yerel kaynaktan kopyalandı"
  } else {
    $api = if ($Surum -eq "latest") { "https://api.github.com/repos/$DEPO/releases/latest" } else { "https://api.github.com/repos/$DEPO/releases/tags/$Surum" }
    $sur = Invoke-RestMethod -Uri $api -Headers @{ "User-Agent" = "modelen-kur" }
    Tamam "sürüm: $($sur.tag_name)"
    foreach ($ad in @("modelen.exe", "modelen-istemci.zip", "SHA256SUMS")) {
      $v = $sur.assets | Where-Object { $_.name -eq $ad }
      if (-not $v) { if ($ad -eq "SHA256SUMS") { continue } else { Hata "$ad bu sürümde yok ($($sur.tag_name)). Sürüm varlıkları: modelen.exe, modelen-istemci.zip." } }
      Invoke-WebRequest -Uri $v.browser_download_url -OutFile (Join-Path $gecici $ad) -Headers @{ "User-Agent" = "modelen-kur" }
    }
    $sumFile = Join-Path $gecici "SHA256SUMS"
    if (Test-Path $sumFile) {
      foreach ($ad in @("modelen.exe", "modelen-istemci.zip")) {
        $beklenen = (Get-Content $sumFile | Where-Object { $_ -match [regex]::Escape($ad) } | Select-Object -First 1) -split "\s+" | Select-Object -First 1
        $gercek = (Get-FileHash (Join-Path $gecici $ad) -Algorithm SHA256).Hash.ToLower()
        if ($beklenen -and $beklenen.ToLower() -ne $gercek) { Hata "$ad özeti SHA256SUMS ile uyuşmuyor; indirme bozuk ya da değiştirilmiş." }
      }
      Tamam "SHA-256 özetleri doğrulandı"
    } else { Write-Host "    UYARI: SHA256SUMS yok; özet doğrulanamadı." -ForegroundColor Yellow }
    Copy-Item (Join-Path $gecici "modelen.exe") (Join-Path $Hedef "modelen.exe") -Force
    Expand-Archive -Path (Join-Path $gecici "modelen-istemci.zip") -DestinationPath $Hedef -Force
  }
  if (-not (Test-Path (Join-Path $Hedef "istemci\isci.py"))) { Hata "kurulum sonrası istemci\isci.py bulunamadı." }

  # ---------------------------------------------------------------- uv + Python ortamı
  Adim "Python ortamı (uv ile; sistem Python'una dokunulmaz)"
  $uvDir = Join-Path $Hedef "arac"
  $uv = Join-Path $uvDir "uv.exe"
  if (-not (Test-Path $uv)) {
    New-Item -ItemType Directory -Force -Path $uvDir | Out-Null
    $zip = Join-Path $gecici "uv.zip"
    Invoke-WebRequest -Uri $UV_URL -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $gecici -Force
    $bulunan = Get-ChildItem -Path $gecici -Recurse -Filter "uv.exe" | Select-Object -First 1
    if (-not $bulunan) { Hata "uv indirildi ama uv.exe bulunamadı." }
    Copy-Item $bulunan.FullName $uv -Force
  }
  $venv = Join-Path $Hedef ".venv"
  if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    & $uv venv $venv --python 3.12 --seed 2>&1 | ForEach-Object { Tamam $_ }
    if ($LASTEXITCODE -ne 0) { Hata "sanal ortam oluşturulamadı." }
  }
  $py = Join-Path $venv "Scripts\python.exe"

  Adim "PyTorch ($CudaSurumu) ve gerekli paketler (birkaç GB; sabırlı olun)"
  $torchIdx = "https://download.pytorch.org/whl/$CudaSurumu"
  & $uv pip install --python $py torch --index-url $torchIdx 2>&1 | ForEach-Object { Tamam $_ }
  if ($LASTEXITCODE -ne 0) { Hata "PyTorch kurulamadı." }
  & $uv pip install --python $py @PAKETLER 2>&1 | ForEach-Object { Tamam $_ }
  if ($LASTEXITCODE -ne 0) { Hata "paketler kurulamadı." }

  # ---------------------------------------------------------------- taban model
  $modelKlasoru = Join-Path $Hedef "models\qwen3-0.6b-base"
  if ($ModelAtla) { Adim "Taban model atlandı (-ModelAtla)" }
  elseif (Test-Path (Join-Path $modelKlasoru "config.json")) { Adim "Taban model zaten var"; Tamam $modelKlasoru }
  else {
    Adim "Taban model indiriliyor ($MODEL, Apache-2.0, ~1.2 GB)"
    New-Item -ItemType Directory -Force -Path $modelKlasoru | Out-Null
    $kod = "from huggingface_hub import snapshot_download; snapshot_download('$MODEL', local_dir=r'$modelKlasoru', allow_patterns=['*.json','*.safetensors','*.txt','merges.txt','vocab.json'])"
    & $py -c $kod 2>&1 | ForEach-Object { Tamam $_ }
    if ($LASTEXITCODE -ne 0) { Hata "model indirilemedi." }
  }

  # ---------------------------------------------------------------- doğrulama
  Adim "Doğrulama"
  $env:PYTHONIOENCODING = "utf-8"
  $dogrula = "import torch; print('torch', torch.__version__, '| CUDA available:', torch.cuda.is_available()); import transformers, peft, safetensors; print('packages ok')"
  & $py -c $dogrula 2>&1 | ForEach-Object { Tamam $_ }
  if ($LASTEXITCODE -ne 0) { Hata "Python ortamı doğrulanamadı." }

  # ---------------------------------------------------------------- kısayol
  Adim "Başlat menüsü kısayolu"
  $exeYolu = Join-Path $Hedef "modelen.exe"
  if (Test-Path $exeYolu) {
    $menu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $ws = New-Object -ComObject WScript.Shell
    $k = $ws.CreateShortcut((Join-Path $menu "Modelen.lnk"))
    $k.TargetPath = $exeYolu; $k.WorkingDirectory = $Hedef; $k.Description = "Modelen gönüllü GPU uygulaması"; $k.Save()
    Tamam "Başlat menüsünde 'Modelen'"
  } else { Tamam "modelen.exe yok; kısayol atlandı" }

  Write-Host "`nKurulum tamam: $Hedef" -ForegroundColor Green
  Write-Host "Başlat menüsünden 'Modelen'i açın. Kaldırmak için $Hedef klasörünü ve Başlat menüsündeki kısayolu silin." -ForegroundColor Green
}
finally {
  Remove-Item -Recurse -Force $gecici -ErrorAction SilentlyContinue
}
