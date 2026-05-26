"""
MaskBridge PRD - PDF敏感情報除去ツール (Flask Webアプリケーション)

複数人で安全に共有できるPDF敏感情報マスキングWebアプリ。
LAN内限定で動作し、アップロードされたPDFから個人情報を自動検出・除去します。
"""

import os
import re
import json
import uuid
import hashlib
import shutil
import logging
import subprocess
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    request,
    render_template,
    send_file,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    abort,
)
from werkzeug.utils import secure_filename

import fitz  # PyMuPDF
import spacy

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"
LOG_FOLDER = BASE_DIR / "logs"
CONFIG_FILE = BASE_DIR / "config.json"

ALLOWED_EXTENSIONS = {"pdf"}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB

FILE_RETENTION_DAYS = 7

DEFAULT_CONFIG = {
    "password": "admin123",
    "port": 5000,
    "host": "0.0.0.0",
    "file_retention_days": FILE_RETENTION_DAYS,
    "max_file_size_mb": 50,
    "mask_char": "█",
    "mask_color_rgb": [0, 0, 0],
}

# ---------------------------------------------------------------------------
# ログ設定
# ---------------------------------------------------------------------------
LOG_FOLDER.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FOLDER / "server.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask アプリ初期化
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
app.secret_key = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------
def load_config() -> dict:
    """設定ファイルを読み込む。存在しなければデフォルト値で新規作成する。"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # 不足キーをデフォルトで補完
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    save_config(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_hash(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def cleanup_old_files() -> None:
    """保持期間を超えたファイルを自動削除する。"""
    cfg = load_config()
    retention = timedelta(days=cfg.get("file_retention_days", FILE_RETENTION_DAYS))
    now = datetime.now()
    for folder in (UPLOAD_FOLDER, OUTPUT_FOLDER):
        if not folder.exists():
            continue
        for item in folder.iterdir():
            if item.is_file():
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if now - mtime > retention:
                    item.unlink()
                    logger.info("古いファイルを削除しました: %s", item.name)


def schedule_cleanup(interval_hours: int = 24) -> None:
    """定期的にファイルクリーンアップを実行するバックグラウンドスレッドを起動。"""
    def _run():
        while True:
            try:
                cleanup_old_files()
            except Exception as e:
                logger.error("クリーンアップエラー: %s", e)
            time.sleep(interval_hours * 3600)

    t = threading.Thread(target=_run, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# 認証デコレータ
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# NLP モデル (spaCy)
# ---------------------------------------------------------------------------
_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("ja_core_news_sm")
            logger.info("spaCy 日本語モデルをロードしました。")
        except OSError:
            logger.warning(
                "spaCy 日本語モデルが見つかりません。"
                " 'python -m spacy download ja_core_news_sm' を実行してください。"
            )
            _nlp = None
    return _nlp


# ---------------------------------------------------------------------------
# 敏感情報検出パターン
# ---------------------------------------------------------------------------
PATTERNS = {
    "電話番号": re.compile(
        r"(?:0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{2,4})"
        r"|(?:\d{2,4}-\d{2,4}-\d{3,4})"
    ),
    "メールアドレス": re.compile(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    ),
    "郵便番号": re.compile(r"〒?\d{3}[-‐ー]\d{4}"),
    "マイナンバー": re.compile(r"\d{4}\s?\d{4}\s?\d{4}"),
    "クレジットカード": re.compile(
        r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"
    ),
    "生年月日": re.compile(
        r"(?:昭和|平成|令和|S|H|R)?\d{1,4}年\d{1,2}月\d{1,2}日"
        r"|(?:19|20)\d{2}[/\-\.]\d{1,2}[/\-\.]\d{1,2}"
    ),
    "口座番号": re.compile(r"(?:普通|当座)\s?\d{7,8}"),
}


def detect_sensitive_text(text: str) -> list[dict]:
    """テキストから敏感情報を正規表現 + NLP で検出して返す。"""
    findings = []

    # 正規表現パターン
    for label, pattern in PATTERNS.items():
        for m in pattern.finditer(text):
            findings.append({
                "type": label,
                "text": m.group(),
                "start": m.start(),
                "end": m.end(),
            })

    # spaCy NER
    nlp = get_nlp()
    if nlp:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "LOC", "FAC"):
                findings.append({
                    "type": f"固有名詞({ent.label_})",
                    "text": ent.text,
                    "start": ent.start_char,
                    "end": ent.end_char,
                })

    return findings


# ---------------------------------------------------------------------------
# OCR ユーティリティ (Tesseract)
# ---------------------------------------------------------------------------
def ocr_page_image(page: fitz.Page) -> str:
    """ページを画像化して Tesseract OCR でテキスト抽出する。"""
    try:
        import pytesseract
        from PIL import Image
        import io

        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang="jpn")
        return text
    except ImportError:
        logger.warning("pytesseract / Pillow がインストールされていません。OCR をスキップします。")
        return ""
    except Exception as e:
        logger.warning("OCR エラー: %s", e)
        return ""


# ---------------------------------------------------------------------------
# PDF マスキング処理
# ---------------------------------------------------------------------------
def mask_pdf(input_path: Path, output_path: Path, mask_options: dict | None = None) -> dict:
    """
    PDF を解析し、検出された敏感情報を黒塗りマスクで除去する。

    Returns:
        処理結果の統計情報を含む dict
    """
    cfg = load_config()
    mask_char = cfg.get("mask_char", "█")
    mask_rgb = cfg.get("mask_color_rgb", [0, 0, 0])
    mask_color = tuple(c / 255.0 for c in mask_rgb)

    use_ocr = (mask_options or {}).get("use_ocr", False)
    selected_types = (mask_options or {}).get("types", list(PATTERNS.keys()))

    doc = fitz.open(str(input_path))
    total_findings = []
    pages_processed = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        # テキストが少ない場合は OCR を試行
        if use_ocr and len(text.strip()) < 10:
            text = ocr_page_image(page)

        findings = detect_sensitive_text(text)

        for finding in findings:
            if finding["type"] not in selected_types and not finding["type"].startswith("固有名詞"):
                continue

            # テキスト位置を検索してマスク描画
            target_text = finding["text"]
            text_instances = page.search_for(target_text)
            for inst in text_instances:
                # 黒塗り矩形を描画
                annot = page.add_redact_annot(inst)
                annot.set_colors(fill=mask_color)
                annot.update()

            finding["page"] = page_num + 1
            total_findings.append(finding)

        # Redaction を適用
        page.apply_redactions()
        pages_processed += 1

    doc.save(str(output_path), garbage=4, deflate=True)
    doc.close()

    stats = {
        "total_findings": len(total_findings),
        "pages_processed": pages_processed,
        "findings": total_findings,
        "input_file": input_path.name,
        "output_file": output_path.name,
        "timestamp": datetime.now().isoformat(),
    }
    logger.info(
        "マスキング完了: %s → %s (%d件検出)",
        input_path.name,
        output_path.name,
        len(total_findings),
    )
    return stats


# ---------------------------------------------------------------------------
# ルーティング
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        cfg = load_config()
        if password == cfg["password"]:
            session["authenticated"] = True
            session.permanent = True
            logger.info("ログイン成功: %s", request.remote_addr)
            return redirect(url_for("dashboard"))
        else:
            logger.warning("ログイン失敗: %s", request.remote_addr)
            flash("パスワードが正しくありません。", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("ログアウトしました。", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    # 処理済みファイル一覧
    output_files = []
    if OUTPUT_FOLDER.exists():
        for f in sorted(OUTPUT_FOLDER.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix.lower() == ".pdf":
                output_files.append({
                    "name": f.name,
                    "size": f"{f.stat().st_size / 1024:.1f} KB",
                    "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
    return render_template("dashboard.html", files=output_files)


@app.route("/upload", methods=["POST"])
@login_required
def upload():
    if "file" not in request.files:
        flash("ファイルが選択されていません。", "error")
        return redirect(url_for("dashboard"))

    file = request.files["file"]
    if file.filename == "":
        flash("ファイルが選択されていません。", "error")
        return redirect(url_for("dashboard"))

    if not allowed_file(file.filename):
        flash("PDFファイルのみアップロード可能です。", "error")
        return redirect(url_for("dashboard"))

    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    filename = secure_filename(file.filename)
    if not filename:
        filename = f"upload_{uuid.uuid4().hex[:8]}.pdf"

    # ユニークなファイル名
    unique_id = uuid.uuid4().hex[:8]
    input_filename = f"{unique_id}_{filename}"
    input_path = UPLOAD_FOLDER / input_filename
    file.save(str(input_path))

    # マスキングオプション
    use_ocr = request.form.get("use_ocr") == "on"
    selected_types = request.form.getlist("mask_types")
    if not selected_types:
        selected_types = list(PATTERNS.keys())

    mask_options = {
        "use_ocr": use_ocr,
        "types": selected_types,
    }

    # マスキング処理
    output_filename = f"masked_{input_filename}"
    output_path = OUTPUT_FOLDER / output_filename

    try:
        stats = mask_pdf(input_path, output_path, mask_options)
        flash(
            f"処理完了: {stats['total_findings']}件の敏感情報を検出・マスキングしました。"
            f"（{stats['pages_processed']}ページ処理）",
            "success",
        )
    except Exception as e:
        logger.error("マスキング処理エラー: %s", e)
        flash(f"処理中にエラーが発生しました: {e}", "error")

    return redirect(url_for("dashboard"))


@app.route("/download/<filename>")
@login_required
def download(filename):
    filepath = OUTPUT_FOLDER / secure_filename(filename)
    if not filepath.exists():
        abort(404)
    return send_file(str(filepath), as_attachment=True)


@app.route("/delete/<filename>", methods=["POST"])
@login_required
def delete_file(filename):
    filepath = OUTPUT_FOLDER / secure_filename(filename)
    if filepath.exists():
        filepath.unlink()
        flash(f"ファイル '{filename}' を削除しました。", "info")
    else:
        flash("ファイルが見つかりません。", "error")
    return redirect(url_for("dashboard"))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    cfg = load_config()
    if request.method == "POST":
        action = request.form.get("action")

        if action == "change_password":
            current = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if current != cfg["password"]:
                flash("現在のパスワードが正しくありません。", "error")
            elif new_pw != confirm:
                flash("新しいパスワードが一致しません。", "error")
            elif len(new_pw) < 6:
                flash("パスワードは6文字以上にしてください。", "error")
            else:
                cfg["password"] = new_pw
                save_config(cfg)
                flash("パスワードを変更しました。", "success")

        elif action == "update_settings":
            try:
                cfg["file_retention_days"] = int(request.form.get("retention_days", 7))
                cfg["max_file_size_mb"] = int(request.form.get("max_file_size", 50))
                save_config(cfg)
                flash("設定を更新しました。", "success")
            except ValueError:
                flash("設定値が正しくありません。", "error")

        elif action == "cleanup_now":
            cleanup_old_files()
            flash("古いファイルのクリーンアップを実行しました。", "success")

        return redirect(url_for("settings"))

    return render_template("settings.html", config=cfg)


@app.route("/api/status")
@login_required
def api_status():
    upload_count = len(list(UPLOAD_FOLDER.iterdir())) if UPLOAD_FOLDER.exists() else 0
    output_count = len(list(OUTPUT_FOLDER.iterdir())) if OUTPUT_FOLDER.exists() else 0
    return jsonify({
        "status": "running",
        "upload_count": upload_count,
        "output_count": output_count,
        "timestamp": datetime.now().isoformat(),
    })


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------
def main():
    # フォルダ作成
    for folder in (UPLOAD_FOLDER, OUTPUT_FOLDER, LOG_FOLDER):
        folder.mkdir(parents=True, exist_ok=True)

    cfg = load_config()

    # 定期クリーンアップ起動
    schedule_cleanup()

    # 初回起動時にモデルをプリロード
    get_nlp()

    host = cfg.get("host", "0.0.0.0")
    port = cfg.get("port", 5000)

    logger.info("=" * 60)
    logger.info("MaskBridge PRD サーバーを起動します")
    logger.info("  アドレス: http://%s:%d", host, port)
    logger.info("  デフォルトパスワード: %s", cfg["password"])
    logger.info("  ファイル保持期間: %d日", cfg.get("file_retention_days", 7))
    logger.info("=" * 60)

    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
