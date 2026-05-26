@echo off
chcp 65001 >nul 2>&1
title MaskBridge PRD - PDF敏感情報除去ツール

echo.
echo ============================================================
echo   MaskBridge PRD - PDF敏感情報除去ツール
echo ============================================================
echo.

REM --- Python 環境チェック ---
set PYTHON_CMD=
for %%P in (python python3 py) do (
    %%P --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=%%P
        goto :python_found
    )
)

echo [エラー] Python が見つかりません。
echo.
echo Python 3.10以上をインストールしてください:
echo   https://www.python.org/downloads/
echo.
echo インストール時に "Add Python to PATH" にチェックを入れてください。
echo.
pause
exit /b 1

:python_found
echo [OK] Python を検出しました:
%PYTHON_CMD% --version
echo.

REM --- Python バージョン確認 ---
for /f "tokens=2 delims= " %%V in ('%PYTHON_CMD% --version 2^>^&1') do set PY_VER=%%V
echo     バージョン: %PY_VER%
echo.

REM --- 必要フォルダの確認 ---
if not exist "%~dp0uploads" mkdir "%~dp0uploads"
if not exist "%~dp0outputs" mkdir "%~dp0outputs"
if not exist "%~dp0logs" mkdir "%~dp0logs"

REM --- サーバーIP確認 ---
echo ============================================================
echo   ネットワーク情報
echo ============================================================
echo.
echo   このPCのIPアドレス:
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4"') do (
    echo     %%A
)
echo.
echo   アクセスURL:
echo     ローカル:     http://localhost:5000
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4"') do (
    echo     ネットワーク: http://%%A:5000
)
echo.
echo ============================================================
echo   サーバーを起動しています...
echo   停止するには Ctrl+C を押してください
echo ============================================================
echo.

REM --- サーバー起動 ---
%PYTHON_CMD% "%~dp0server_app.py" 2>>"%~dp0logs\server_error.log"

if errorlevel 1 (
    echo.
    echo ============================================================
    echo   [エラー] サーバーの起動に失敗しました
    echo ============================================================
    echo.
    echo   エラーログを確認してください:
    echo     %~dp0logs\server_error.log
    echo.
    echo   よくある原因:
    echo     - ポート5000が既に使用中
    echo     - 必要なライブラリが未インストール
    echo     - setup.ps1 を先に実行してください
    echo.
    pause
    exit /b 1
)

pause
