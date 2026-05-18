# プロキシｸﾝ

社内ネットワーク向けのプロキシ切り替えツールです。

## ダウンロード

**[Releases ページ](../../releases/latest)** から `proxy_switcher.zip` をダウンロードして解凍し、`proxy_switcher.exe` をダブルクリックするだけで使えます。インストール不要です。

## 機能

| セクション | 内容 |
|---|---|
| システムプロキシ | Windowsのシステムプロキシ（レジストリ）をON/OFF |
| npm プロキシ | `npm config` のプロキシ設定をON/OFF |
| 環境変数プロキシ | `HTTP_PROXY` / `HTTPS_PROXY` 環境変数をON/OFF（Claude Code用） |
| BAT ファイル | 任意の `.bat` ファイルを選択して実行 |

各セクションでプロキシアドレスを選択してON/OFFを切り替えます。起動時に現在の設定値を表示します。

## 動作環境

- Windows 10 / 11
- Python 3.x（ソースから実行する場合）
- npm（npmプロキシ機能を使う場合）

## 使い方

### EXEを使う場合（推奨）

1. [Releases ページ](../../releases/latest) から `proxy_switcher.zip` をダウンロード
2. 任意の場所に解凍
3. `proxy_switcher.exe` をダブルクリックで起動

### Pythonから直接実行する場合

```
python proxy_switcher.py
```

## EXE化の方法

### 1. 依存ライブラリのインストール

```
pip install pyinstaller Pillow
```

### 2. ビルド

```
pyinstaller proxy_switcher.spec
```

ビルド完了後、`dist/proxy_switcher/` フォルダ内に `proxy_switcher.exe` が生成されます。

> **注意:** `dist/proxy_switcher/` フォルダごと配布してください。EXE単体では動作しません。

### 3. 初回起動時の設定

起動後、「BAT ファイル」セクションから任意の `.bat` ファイルを設定できます。設定は `config.ini` に保存されます（gitには含まれません）。

## 環境変数プロキシについて

`setx` コマンドで環境変数を永続的に設定するため、**ONにした後は新しいターミナルを開いてから有効になります**。

Claude Code の `ECONNREFUSED` エラーが出る場合はこのセクションでプロキシをONにしてください。
