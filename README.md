# MaskBridge PRD - PDF敏感情報除去ツール

複数人で安全に共有できる **PDF敏感情報マスキング Web アプリケーション**です。  
LAN 内のサーバー PC で起動し、同じネットワーク上のスタッフ PC のブラウザからアクセスして利用します。

---

## 目次

1. [必要な環境](#必要な環境)
2. [インストール手順](#インストール手順)
3. [起動方法](#起動方法)
4. [Tesseract-OCR のインストール](#tesseract-ocr-のインストール)
5. [ファイアウォール設定](#ファイアウォール設定)
6. [運用マニュアル](#運用マニュアル)
7. [トラブルシューティング](#トラブルシューティング)
8. [セキュリティチェックリスト](#セキュリティチェックリスト)
9. [FAQ（よくある質問）](#faqよくある質問)

---

## 必要な環境

| 項目 | 要件 |
|------|------|
| **OS** | Windows 10 / 11（64bit） |
| **Python** | 3.10 以上 |
| **メモリ** | 4 GB 以上推奨 |
| **ディスク** | 1 GB 以上の空き容量 |
| **ネットワーク** | LAN 接続（同一ネットワーク内） |
| **ブラウザ** | Chrome / Edge / Firefox（最新版推奨） |

### オプション

| 項目 | 用途 |
|------|------|
| **Tesseract-OCR** | 画像 PDF の OCR 処理（スキャン PDF 対応） |

---

## インストール手順

### ステップ 1: Python のインストール

1. [Python 公式サイト](https://www.python.org/downloads/) にアクセス
2. **Python 3.10 以上** のインストーラーをダウンロード
3. インストーラーを実行し、**「Add Python to PATH」にチェック**を入れてインストール

> **確認方法:** PowerShell で以下を実行
> ```powershell
> python --version
> ```
> `Python 3.10.x` 以上が表示されれば OK です。

### ステップ 2: プロジェクトの配置

1. このリポジトリをダウンロードまたは `git clone` します
2. 任意のフォルダに展開します（例: `C:\MaskBridge_PRD`）

```powershell
git clone https://github.com/hg1515-inv/MaskBridge_PRD.git
cd MaskBridge_PRD
```

### ステップ 3: 自動セットアップの実行

PowerShell を **管理者権限** で開き、以下を実行します:

```powershell
# 実行ポリシーを一時的に変更
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# セットアップスクリプトを実行
.\setup.ps1
```

セットアップスクリプトが自動的に以下を行います:

- [x] Python 3.10 以上の確認
- [x] pip ライブラリの一括インストール
- [x] spaCy 日本語モデル (`ja_core_news_sm`) のダウンロード
- [x] フォルダ構成 (`uploads/`, `outputs/`, `logs/`) の自動作成
- [x] Tesseract-OCR のインストール確認
- [x] 設定ファイル (`config.json`) の初期化

#### セットアップオプション

```powershell
# Tesseract-OCR の確認をスキップ
.\setup.ps1 -SkipTesseract

# spaCy モデルのダウンロードをスキップ
.\setup.ps1 -SkipSpacy

# 設定ファイルを強制的に再作成
.\setup.ps1 -Force
```

### ステップ 4: インストール完了チェックリスト

| # | 確認項目 | コマンド |
|---|----------|----------|
| 1 | Python バージョン | `python --version` → 3.10 以上 |
| 2 | Flask インストール | `python -c "import flask; print(flask.__version__)"` |
| 3 | PyMuPDF インストール | `python -c "import fitz; print(fitz.version)"` |
| 4 | spaCy モデル | `python -c "import spacy; spacy.load('ja_core_news_sm')"` |
| 5 | フォルダ構成 | `uploads/`, `outputs/`, `logs/` が存在 |
| 6 | config.json | プロジェクトルートに存在 |

---

## 起動方法

### サーバー PC（ツールをホストする PC）

#### 方法 1: バッチファイルで起動（推奨）

`start_server.bat` をダブルクリックするだけで起動できます。

- Python 環境を自動チェック
- サーバー IP・ポートを自動表示
- エラー時はログファイルに記録

#### 方法 2: コマンドラインで起動

```powershell
cd C:\MaskBridge_PRD
python server_app.py
```

起動すると以下が表示されます:

```
============================================================
MaskBridge PRD サーバーを起動します
  アドレス: http://0.0.0.0:5000
  デフォルトパスワード: admin123
  ファイル保持期間: 7日
============================================================
```

### サーバー IP の確認方法

サーバー PC で以下のコマンドを実行します:

```powershell
ipconfig
```

表示される **IPv4 アドレス**（例: `192.168.1.100`）がサーバーの IP アドレスです。

```
イーサネット アダプター:
   IPv4 アドレス . . . . . . : 192.168.1.100
```

### スタッフ PC（ブラウザからアクセスする PC）

1. サーバー PC と **同じネットワーク（LAN）** に接続
2. ブラウザを開き、以下の URL にアクセス:

```
http://<サーバーIPアドレス>:5000
```

例: `http://192.168.1.100:5000`

3. パスワードを入力してログイン（デフォルト: `admin123`）

---

## Tesseract-OCR のインストール

画像 PDF（スキャンした PDF）からテキストを読み取るには、Tesseract-OCR が必要です。

### ダウンロード

- **Windows 用インストーラー:**  
  [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)

### インストール手順

1. 上記リンクから最新の `.exe` インストーラーをダウンロード
2. インストーラーを実行
3. **「Additional language data」** の画面で **「Japanese」** にチェックを入れる
4. インストール先（デフォルト: `C:\Program Files\Tesseract-OCR`）を確認してインストール
5. **環境変数 PATH に追加:**

```powershell
# システム環境変数に Tesseract のパスを追加
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";C:\Program Files\Tesseract-OCR",
    [EnvironmentVariableTarget]::Machine
)
```

6. PowerShell を再起動して確認:

```powershell
tesseract --version
```

> **注意:** Tesseract-OCR がなくても、テキスト埋め込み PDF のマスキングは正常に動作します。  
> OCR 機能はスキャン PDF を処理する場合にのみ必要です。

---

## ファイアウォール設定

他の PC からアクセスするには、サーバー PC のファイアウォールでポート 5000 を開放する必要があります。

### PowerShell（管理者権限）で実行

```powershell
# ポート5000を許可するルールを追加
netsh advfirewall firewall add rule name="MaskBridge PRD" dir=in action=allow protocol=TCP localport=5000

# ルールの確認
netsh advfirewall firewall show rule name="MaskBridge PRD"
```

### ルールの削除（不要になった場合）

```powershell
netsh advfirewall firewall delete rule name="MaskBridge PRD"
```

> **セキュリティ注意:** ポート開放はLAN内限定です。  
> インターネットに公開する場合は追加のセキュリティ対策が必要です（非推奨）。

---

## 運用マニュアル

### パスワードの変更

1. ブラウザでログイン後、ナビゲーションバーの **「設定」** をクリック
2. **「パスワード変更」** セクションで現在のパスワードと新しいパスワードを入力
3. **「パスワードを変更」** をクリック

> **重要:** 初回ログイン後、必ずデフォルトパスワード (`admin123`) を変更してください。

### ファイルの手動削除

#### 方法 1: Web UI から削除

- ダッシュボードの処理済みファイル一覧から **「削除」** ボタンをクリック

#### 方法 2: 設定画面から一括クリーンアップ

- 設定画面の **「メンテナンス」** セクションで **「古いファイルをクリーンアップ」** をクリック
- 保持期間（デフォルト: 7 日）を超えたファイルが削除されます

#### 方法 3: 手動でフォルダを削除

```powershell
# アップロードファイルを全削除
Remove-Item -Path "C:\MaskBridge_PRD\uploads\*" -Force

# 処理済みファイルを全削除
Remove-Item -Path "C:\MaskBridge_PRD\outputs\*" -Force
```

### 自動削除の設定

`config.json` でファイル保持期間を変更できます:

```json
{
  "file_retention_days": 7
}
```

サーバー起動中は 24 時間ごとに自動クリーンアップが実行されます。

### サーバーの停止

- バッチファイルで起動した場合: ウィンドウで `Ctrl + C` を押す
- コマンドラインで起動した場合: `Ctrl + C` を押す

---

## トラブルシューティング

### サーバーが起動しない

| 症状 | 対処法 |
|------|--------|
| `ModuleNotFoundError` | `setup.ps1` を再実行してライブラリをインストール |
| `Address already in use` | 別のプログラムがポート 5000 を使用中。`netstat -ano \| findstr :5000` で確認し、該当プロセスを終了 |
| `Python が見つかりません` | Python を PATH に追加してインストールし直す |

### 他の PC からアクセスできない

| 症状 | 対処法 |
|------|--------|
| 接続がタイムアウト | ファイアウォールでポート 5000 を開放（[ファイアウォール設定](#ファイアウォール設定)参照） |
| 接続が拒否される | サーバーが起動しているか確認。`http://localhost:5000` でサーバー PC 自体からアクセスできるか確認 |
| IP アドレスが分からない | サーバー PC で `ipconfig` を実行して IPv4 アドレスを確認 |
| 異なるサブネット | 両方の PC が同じネットワーク（同じルーター）に接続されているか確認 |

### マスキングが正しく動作しない

| 症状 | 対処法 |
|------|--------|
| テキストが検出されない | PDF がテキスト埋め込みか確認。画像 PDF の場合は OCR オプションを有効にする |
| OCR が動作しない | Tesseract-OCR がインストールされ PATH に追加されているか確認 |
| 日本語名が検出されない | spaCy モデルがインストールされているか確認: `python -m spacy download ja_core_news_sm` |

### ログの確認

```powershell
# サーバーログを確認
Get-Content -Path "C:\MaskBridge_PRD\logs\server.log" -Tail 50

# エラーログを確認
Get-Content -Path "C:\MaskBridge_PRD\logs\server_error.log" -Tail 50
```

---

## セキュリティチェックリスト

### 初期設定時

- [ ] デフォルトパスワード (`admin123`) を変更した
- [ ] ファイアウォールでポート 5000 を LAN 内のみに制限した
- [ ] サーバー PC に物理的なアクセス制限がある
- [ ] Windows Update が最新の状態である

### 運用時

- [ ] 定期的にパスワードを変更している
- [ ] 不要なファイルを定期的に削除している
- [ ] サーバーログを定期的に確認している
- [ ] インターネットに直接公開していない

### セキュリティベストプラクティス

1. **パスワード管理:** 推測されにくいパスワード（英数字記号混合 12 文字以上）を設定
2. **ネットワーク分離:** 可能であれば専用 VLAN でサーバーを運用
3. **定期メンテナンス:** 週 1 回はログ確認・ファイルクリーンアップを実施
4. **アクセス制限:** 必要なスタッフのみにパスワードを共有
5. **バックアップ:** 処理前の元 PDF は別途安全な場所に保管
6. **ログ監視:** 不審なログイン試行がないか定期的に確認

---

## FAQ（よくある質問）

### Q: インターネット接続は必要ですか？

**A:** 初回セットアップ時のみ必要です（ライブラリのダウンロード）。  
セットアップ完了後はオフライン環境でも動作します。

### Q: 同時に何人までアクセスできますか？

**A:** Flask の開発サーバーを使用しているため、同時接続は 5〜10 人程度を推奨します。  
大規模利用の場合は Waitress や Gunicorn（Windows は Waitress 推奨）の導入を検討してください。

### Q: 処理済み PDF はどこに保存されますか？

**A:** プロジェクトフォルダ内の `outputs/` ディレクトリに保存されます。  
デフォルトで 7 日後に自動削除されます。

### Q: ポート番号を変更できますか？

**A:** `config.json` の `"port"` を変更してサーバーを再起動してください。  
ファイアウォール設定も合わせて変更が必要です。

```json
{
  "port": 8080
}
```

### Q: 対応している敏感情報の種類は？

**A:** 以下の情報を自動検出・マスキングします:

- 電話番号
- メールアドレス
- 郵便番号
- マイナンバー
- クレジットカード番号
- 生年月日
- 口座番号
- 人名・組織名・地名（spaCy NLP）

### Q: マスキング処理はどの程度の時間がかかりますか？

**A:** PDF のページ数やテキスト量によりますが、一般的な文書（10 ページ程度）であれば数秒で完了します。  
OCR を使用する場合は処理時間が長くなります（1 ページあたり 5〜10 秒程度）。

---

## フォルダ構成

```
MaskBridge_PRD/
├── server_app.py          # Flask サーバー（メインアプリ）
├── requirements.txt       # Python ライブラリ一覧
├── config.json            # 設定ファイル（自動生成）
├── setup.ps1              # PowerShell セットアップスクリプト
├── start_server.bat       # Windows 起動バッチファイル
├── README.md              # このドキュメント
├── .gitignore             # Git 除外設定
├── templates/             # HTML テンプレート
│   ├── login.html         # ログイン画面
│   ├── dashboard.html     # ダッシュボード画面
│   └── settings.html      # 設定画面
├── uploads/               # アップロードファイル（自動作成）
├── outputs/               # 処理済みファイル（自動作成）
└── logs/                  # ログファイル（自動作成）
```

---

## ライセンス

このプロジェクトは社内利用を想定しています。
