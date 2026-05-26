# =============================================================================
# MaskBridge PRD - Windows セットアップスクリプト
# =============================================================================
# 実行方法:
#   PowerShell を管理者権限で開き、以下を実行:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\setup.ps1
# =============================================================================

param(
    [switch]$SkipTesseract,
    [switch]$SkipSpacy,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# --- ヘルパー関数 -----------------------------------------------------------

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[*] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "[X] $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Gray
}

# --- メイン処理 -------------------------------------------------------------

Write-Header "MaskBridge PRD セットアップ"
Write-Host "PDF敏感情報除去ツール - 自動インストーラー" -ForegroundColor White
Write-Host ""

# 1. Python バージョン確認 ---------------------------------------------------
Write-Header "1/6 Python バージョン確認"

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 10) {
                $pythonCmd = $cmd
                Write-Step "Python $($Matches[0]) を検出しました ($cmd)"
                break
            } else {
                Write-Warn "$cmd: Python $($Matches[0]) (3.10以上が必要です)"
            }
        }
    } catch {
        # コマンドが見つからない場合はスキップ
    }
}

if (-not $pythonCmd) {
    Write-Err "Python 3.10以上が見つかりません。"
    Write-Host ""
    Write-Host "以下のURLからPythonをインストールしてください:" -ForegroundColor White
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "インストール時に 'Add Python to PATH' にチェックを入れてください。" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Enterキーを押して終了"
    exit 1
}

# 2. pip ライブラリ一括インストール ------------------------------------------
Write-Header "2/6 pip ライブラリインストール"

$requirementsFile = Join-Path $ScriptDir "requirements.txt"
if (Test-Path $requirementsFile) {
    Write-Step "requirements.txt からライブラリをインストール中..."
    & $pythonCmd -m pip install --upgrade pip 2>&1 | Out-Null
    & $pythonCmd -m pip install -r $requirementsFile
    if ($LASTEXITCODE -ne 0) {
        Write-Err "ライブラリのインストールに失敗しました。"
        Write-Host "手動で実行してください: $pythonCmd -m pip install -r requirements.txt"
        Read-Host "Enterキーを押して終了"
        exit 1
    }
    Write-Step "ライブラリのインストールが完了しました。"
} else {
    Write-Err "requirements.txt が見つかりません: $requirementsFile"
    exit 1
}

# 3. spaCy 日本語モデルのダウンロード ----------------------------------------
Write-Header "3/6 spaCy 日本語モデル"

if (-not $SkipSpacy) {
    Write-Step "spaCy 日本語モデル (ja_core_news_sm) をダウンロード中..."
    & $pythonCmd -m spacy download ja_core_news_sm
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "spaCy モデルのダウンロードに失敗しました。"
        Write-Warn "手動で実行してください: $pythonCmd -m spacy download ja_core_news_sm"
        Write-Warn "NLP機能なしでも基本的なマスキングは動作します。"
    } else {
        Write-Step "spaCy 日本語モデルのインストールが完了しました。"
    }
} else {
    Write-Warn "spaCy モデルのダウンロードをスキップしました。"
}

# 4. Tesseract-OCR の確認 ---------------------------------------------------
Write-Header "4/6 Tesseract-OCR 確認"

if (-not $SkipTesseract) {
    $tesseractFound = $false

    # PATH から検索
    try {
        $tesseractVer = & tesseract --version 2>&1
        if ($tesseractVer -match "tesseract") {
            Write-Step "Tesseract-OCR を検出しました。"
            Write-Info $tesseractVer[0]
            $tesseractFound = $true
        }
    } catch {}

    # 一般的なインストールパスを確認
    if (-not $tesseractFound) {
        $tesseractPaths = @(
            "C:\Program Files\Tesseract-OCR\tesseract.exe",
            "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
        )
        foreach ($tp in $tesseractPaths) {
            if (Test-Path $tp) {
                Write-Step "Tesseract-OCR を検出しました: $tp"
                Write-Info "PATH に追加することを推奨します。"
                $tesseractFound = $true
                break
            }
        }
    }

    if (-not $tesseractFound) {
        Write-Warn "Tesseract-OCR がインストールされていません。"
        Write-Host ""
        Write-Host "  画像PDFのOCR機能を使用するにはTesseract-OCRが必要です。" -ForegroundColor White
        Write-Host "  ダウンロード: https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  インストール手順:" -ForegroundColor White
        Write-Host "    1. 上記URLから Windows installer をダウンロード" -ForegroundColor Gray
        Write-Host "    2. インストール時に 'Japanese' 言語データを追加選択" -ForegroundColor Gray
        Write-Host "    3. インストール先を PATH 環境変数に追加" -ForegroundColor Gray
        Write-Host ""
        Write-Warn "OCR機能なしでもテキストPDFのマスキングは動作します。"
    }
} else {
    Write-Warn "Tesseract-OCR の確認をスキップしました。"
}

# 5. フォルダ構成の自動作成 --------------------------------------------------
Write-Header "5/6 フォルダ構成作成"

$folders = @("uploads", "outputs", "logs", "templates")
foreach ($folder in $folders) {
    $path = Join-Path $ScriptDir $folder
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Step "フォルダを作成しました: $folder\"
    } else {
        Write-Info "フォルダは既に存在します: $folder\"
    }
}

# 6. 設定ファイルの初期化 ---------------------------------------------------
Write-Header "6/6 設定ファイル初期化"

$configFile = Join-Path $ScriptDir "config.json"
if (-not (Test-Path $configFile) -or $Force) {
    $defaultConfig = @{
        password = "admin123"
        port = 5000
        host = "0.0.0.0"
        file_retention_days = 7
        max_file_size_mb = 50
        mask_char = [char]0x2588  # █
        mask_color_rgb = @(0, 0, 0)
    }
    $defaultConfig | ConvertTo-Json -Depth 3 | Out-File -Encoding UTF8 $configFile
    Write-Step "設定ファイルを作成しました: config.json"
    Write-Warn "デフォルトパスワード: admin123（変更を強く推奨します）"
} else {
    Write-Info "設定ファイルは既に存在します: config.json"
}

# --- 完了 -------------------------------------------------------------------
Write-Header "セットアップ完了"

Write-Host "  全てのセットアップが完了しました！" -ForegroundColor Green
Write-Host ""
Write-Host "  【次のステップ】" -ForegroundColor White
Write-Host "    1. start_server.bat をダブルクリックしてサーバーを起動" -ForegroundColor Gray
Write-Host "    2. ブラウザで http://localhost:5000 にアクセス" -ForegroundColor Gray
Write-Host "    3. パスワード: admin123 でログイン" -ForegroundColor Gray
Write-Host "    4. 設定画面からパスワードを変更" -ForegroundColor Gray
Write-Host ""
Write-Host "  【他のPCからアクセスする場合】" -ForegroundColor White
Write-Host "    1. ipconfig コマンドでサーバーPCのIPアドレスを確認" -ForegroundColor Gray
Write-Host "    2. ブラウザで http://<サーバーIP>:5000 にアクセス" -ForegroundColor Gray
Write-Host ""
Write-Host "  【ファイアウォール設定（管理者権限が必要）】" -ForegroundColor White
Write-Host "    netsh advfirewall firewall add rule name=`"MaskBridge`" dir=in action=allow protocol=TCP localport=5000" -ForegroundColor Yellow
Write-Host ""

Read-Host "Enterキーを押して終了"
