import ctypes
# Windows DPI スケーリング対応（文字ぼやけ防止）—— tkinter より前に宣言
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)   # Per-Monitor DPI Aware v2 (Win10+)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()    # フォールバック
    except Exception:
        pass

import winreg
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import configparser
import threading
import os

# subprocess でコンソールウィンドウを非表示にするフラグ
NOWND = subprocess.CREATE_NO_WINDOW

# iniファイルのパス
INI_FILE_PATH = "config.ini"

DEFAULT_PROXY_LIST = [
    "172.20.15.153:8080",
    "172.20.4.3:8080",
]

PROXY_LIST = []

# GUIのルートウィンドウ参照（スレッドからのコールバック用）
root_ref = None

# セクション定義（key, 表示名）順番が表示順
SECTION_KEYS = [
    ("systemproxy", "システムプロキシ"),
    ("npmproxy",    "npm プロキシ"),
    ("envproxy",    "環境変数プロキシ  (Claude Code用)"),
    ("iplist",      "IPリスト管理"),
    ("vpn",         "VPN 接続"),
    ("batfile",     "BAT ファイル"),
]

# key -> tk.BooleanVar（True=表示）
visibility_vars = {}
# key -> LabelFrame ウィジェット
section_frames = {}

# ─────────────────────────────────────────────────
# ini ファイル
# ─────────────────────────────────────────────────

def load_ini():
    config = configparser.ConfigParser()
    config.read(INI_FILE_PATH, encoding="utf-8")
    if "Settings" not in config:
        config["Settings"] = {}
    if "Visibility" not in config:
        config["Visibility"] = {}
    return config

def save_ini(config):
    with open(INI_FILE_PATH, "w", encoding="utf-8") as f:
        config.write(f)

# ─────────────────────────────────────────────────
# 表示設定
# ─────────────────────────────────────────────────

def load_visibility(config):
    """INIから各セクションの表示フラグを読み込む（デフォルトはすべて表示）"""
    vis = config["Visibility"]
    for key, _ in SECTION_KEYS:
        default = True
        visibility_vars[key] = tk.BooleanVar(value=vis.get(key, "true").lower() != "false")

def save_visibility():
    """現在の表示状態をINIに書き込む"""
    config = load_ini()
    for key, _ in SECTION_KEYS:
        config["Visibility"][key] = "true" if visibility_vars[key].get() else "false"
    save_ini(config)

def apply_visibility():
    """section_framesをvisibility_varsに従ってpack/pack_forgetし直す"""
    PACK_OPTS = dict(pady=6, fill=tk.X, padx=10)
    for key, _ in SECTION_KEYS:
        frame = section_frames.get(key)
        if frame:
            frame.pack_forget()
    for key, _ in SECTION_KEYS:
        frame = section_frames.get(key)
        if frame and visibility_vars[key].get():
            frame.pack(**PACK_OPTS)
    root_ref.update_idletasks()
    save_visibility()

def open_visibility_settings():
    """表示設定ダイアログ（ctk版）"""
    dialog = ctk.CTkToplevel(root_ref)
    dialog.title("表示設定")
    dialog.configure(fg_color=PANEL_BG)
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.after(50, dialog.focus_set)

    ctk.CTkLabel(dialog, text="SECTIONS",
                 text_color=TEXT2,
                 font=ctk.CTkFont("Meiryo UI", 10, "bold")).pack(
                     padx=24, pady=(16, 8), anchor="w")

    for key, label in SECTION_KEYS:
        ctk.CTkCheckBox(
            dialog, text=label,
            variable=visibility_vars[key],
            command=apply_visibility,
            text_color=TEXT1,
            fg_color=BTN_NEU_H,
            hover_color=BTN_NEU,
            checkmark_color="#ffffff",
            font=ctk.CTkFont("Meiryo UI", 10),
        ).pack(padx=24, pady=3, anchor="w")

    ctk.CTkButton(dialog, text="閉じる",
                  command=dialog.destroy,
                  fg_color=BTN_NEU, hover_color=BTN_NEU_H,
                  corner_radius=16, height=32, width=110,
                  font=ctk.CTkFont("Meiryo UI", 10, "bold")).pack(pady=(14, 18))

# ─────────────────────────────────────────────────
# プロキシ共通
# ─────────────────────────────────────────────────

def get_system_proxy_status():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                             0, winreg.KEY_READ)
        try:
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not enabled:
                return None
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
            return server if server else None
        except FileNotFoundError:
            return None
        finally:
            winreg.CloseKey(key)
    except Exception:
        return None

def set_system_proxy():
    try:
        selected = listbox.curselection()
        if not selected:
            messagebox.showwarning("警告", "プロキシを選択してください")
            return
        proxy_address = PROXY_LIST[selected[0]]
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                             0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_address)
        winreg.CloseKey(key)
        ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
        ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)
        system_status_label.config(text=f"現在: {proxy_address}")
        messagebox.showinfo("成功", f"プロキシを設定しました:\n{proxy_address}")
    except Exception as e:
        messagebox.showerror("エラー", f"プロキシ設定中にエラーが発生しました: {e}")

def disable_system_proxy():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                             0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
        ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)
        system_status_label.config(text="現在: 無効")
        messagebox.showinfo("成功", "プロキシを無効にしました")
    except Exception as e:
        messagebox.showerror("エラー", f"プロキシ無効化中にエラーが発生しました: {e}")

# ─────────────────────────────────────────────────
# プロキシリスト管理
# ─────────────────────────────────────────────────

def load_proxy_list():
    global PROXY_LIST
    config = load_ini()
    raw = config["Settings"].get("proxylist", "")
    PROXY_LIST = [p.strip() for p in raw.split(",") if p.strip()] if raw.strip() else list(DEFAULT_PROXY_LIST)

def save_proxy_list():
    config = load_ini()
    config["Settings"]["proxylist"] = ",".join(PROXY_LIST)
    save_ini(config)

def refresh_all_listboxes():
    for lb in (listbox, npm_listbox, env_listbox, mgmt_listbox):
        lb.delete(0, tk.END)
        for proxy in PROXY_LIST:
            lb.insert(tk.END, proxy)

def add_proxy():
    value = entry_var.get().strip()
    if not value:
        messagebox.showwarning("警告", "IPアドレスを入力してください")
        return
    if ":" not in value:
        messagebox.showwarning("警告", "形式は「IPアドレス:ポート」で入力してください\n例: 172.20.15.153:8080")
        return
    if value in PROXY_LIST:
        messagebox.showwarning("警告", "すでに登録されています")
        return
    PROXY_LIST.append(value)
    save_proxy_list()
    refresh_all_listboxes()
    entry_var.set("")

def remove_proxy():
    selected = mgmt_listbox.curselection()
    if not selected:
        messagebox.showwarning("警告", "削除するアドレスを選択してください")
        return
    if len(PROXY_LIST) <= 1:
        messagebox.showwarning("警告", "リストは1件以上必要です")
        return
    PROXY_LIST.pop(selected[0])
    save_proxy_list()
    refresh_all_listboxes()

# ─────────────────────────────────────────────────
# npm プロキシ
# ─────────────────────────────────────────────────

def get_npm_proxy_status():
    try:
        result = subprocess.run("npm config get proxy",
                                capture_output=True, text=True, timeout=5, shell=True, creationflags=NOWND)
        value = result.stdout.strip()
        return value if value and value != "null" else None
    except Exception:
        return None

def set_npm_proxy():
    try:
        selected = npm_listbox.curselection()
        if not selected:
            messagebox.showwarning("警告", "プロキシを選択してください")
            return
        proxy_url = f"http://{PROXY_LIST[selected[0]]}"
        subprocess.run(f"npm config set proxy {proxy_url}", check=True, timeout=10, shell=True, creationflags=NOWND)
        subprocess.run(f"npm config set https-proxy {proxy_url}", check=True, timeout=10, shell=True, creationflags=NOWND)
        npm_status_label.config(text=f"現在: {proxy_url}")
        messagebox.showinfo("成功", f"npmプロキシを設定しました:\n{proxy_url}")
    except FileNotFoundError:
        messagebox.showerror("エラー", "npmが見つかりません。")
    except Exception as e:
        messagebox.showerror("エラー", f"npmプロキシ設定中にエラーが発生しました: {e}")

def disable_npm_proxy():
    try:
        subprocess.run("npm config delete proxy", check=True, timeout=10, shell=True, creationflags=NOWND)
        subprocess.run("npm config delete https-proxy", check=True, timeout=10, shell=True, creationflags=NOWND)
        npm_status_label.config(text="現在: 無効")
        messagebox.showinfo("成功", "npmプロキシを無効にしました")
    except FileNotFoundError:
        messagebox.showerror("エラー", "npmが見つかりません。")
    except Exception as e:
        messagebox.showerror("エラー", f"npmプロキシ無効化中にエラーが発生しました: {e}")

# ─────────────────────────────────────────────────
# 環境変数プロキシ
# ─────────────────────────────────────────────────

def get_env_proxy_status():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, "HTTP_PROXY")
            return value if value else None
        except FileNotFoundError:
            return None
        finally:
            winreg.CloseKey(key)
    except Exception:
        return None

def set_env_proxy():
    try:
        selected = env_listbox.curselection()
        if not selected:
            messagebox.showwarning("警告", "プロキシを選択してください")
            return
        proxy_url = f"http://{PROXY_LIST[selected[0]]}"
        subprocess.run(f'setx HTTP_PROXY "{proxy_url}"', check=True, shell=True, timeout=10)
        subprocess.run(f'setx HTTPS_PROXY "{proxy_url}"', check=True, shell=True, timeout=10)
        subprocess.run('setx NODE_USE_ENV_PROXY 1', check=True, shell=True, timeout=10)
        env_status_label.config(text=f"現在: {proxy_url}")
        messagebox.showinfo("成功", f"環境変数プロキシを設定しました:\n{proxy_url}\n\n※新しいターミナルを開いてから有効になります")
    except Exception as e:
        messagebox.showerror("エラー", f"環境変数プロキシ設定中にエラーが発生しました: {e}")

def disable_env_proxy():
    try:
        subprocess.run('setx HTTP_PROXY ""', check=True, shell=True, timeout=10)
        subprocess.run('setx HTTPS_PROXY ""', check=True, shell=True, timeout=10)
        env_status_label.config(text="現在: 無効")
        messagebox.showinfo("成功", "環境変数プロキシを無効にしました\n\n※新しいターミナルを開いてから有効になります")
    except Exception as e:
        messagebox.showerror("エラー", f"環境変数プロキシ無効化中にエラーが発生しました: {e}")

# ─────────────────────────────────────────────────
# BAT ファイル
# ─────────────────────────────────────────────────

def run_bat_file():
    try:
        config = load_ini()
        bat_path = config["Settings"].get("batpath", "")
        if not bat_path:
            messagebox.showwarning("警告", "batファイルが設定されていません")
            return
        threading.Thread(target=execute_bat, args=(bat_path,), daemon=True).start()
    except Exception as e:
        messagebox.showerror("エラー", f"batファイル実行中にエラーが発生しました: {e}")

def execute_bat(bat_path):
    try:
        if not os.path.isabs(bat_path):
            bat_path = os.path.abspath(bat_path)
        if not os.path.exists(bat_path):
            messagebox.showerror("エラー", f"指定されたbatファイルが存在しません: {bat_path}")
            return
        subprocess.call(f'start cmd /K "{bat_path}"', shell=True)
    except Exception as e:
        messagebox.showerror("エラー", f"batファイル実行中にエラーが発生しました: {e}")

def select_bat_file():
    try:
        file_path = filedialog.askopenfilename(
            title="batファイルを選択",
            filetypes=[("BATファイル", "*.bat")],
        )
        if not file_path:
            return
        config = load_ini()
        config["Settings"]["batpath"] = file_path
        save_ini(config)
        bat_label.config(text=f"設定: {file_path}")
        messagebox.showinfo("成功", "batファイルのパスを設定しました")
    except Exception as e:
        messagebox.showerror("エラー", f"batファイル選択中にエラーが発生しました: {e}")

# ─────────────────────────────────────────────────
# VPN 接続
# ─────────────────────────────────────────────────

def set_ras_credentials(vpn_name, username, password):
    """
    rasapi32.dll の RasSetCredentialsW を使ってVPN接続の認証情報を登録する。
    rasphone ダイアログはこの情報を読んでID・PW欄を自動入力する。
    """
    import ctypes
    from ctypes import wintypes

    RASCM_UserName = 0x00000001
    RASCM_Password = 0x00000002

    class RASCREDENTIALS(ctypes.Structure):
        _fields_ = [
            ("dwSize",     wintypes.DWORD),
            ("dwMask",     wintypes.DWORD),
            ("szUserName", ctypes.c_wchar * 257),
            ("szPassword", ctypes.c_wchar * 257),
            ("szDomain",   ctypes.c_wchar * 16),
        ]

    try:
        rasapi32 = ctypes.WinDLL("rasapi32.dll")
        creds = RASCREDENTIALS()
        creds.dwSize     = ctypes.sizeof(RASCREDENTIALS)
        creds.dwMask     = RASCM_UserName | RASCM_Password
        creds.szUserName = username
        creds.szPassword = password
        # 第1引数 NULL = デフォルトのphonebookを使用
        ret = rasapi32.RasSetCredentialsW(None, vpn_name, ctypes.byref(creds), False)
        return ret  # 0 = SUCCESS
    except Exception:
        return -1

def get_vpn_list():
    """WindowsのVPN接続一覧を rasdial で取得する（PowerShellより高速・安定）"""
    try:
        # rasdial を引数なしで実行すると現在のVPN一覧（登録済み含む）は取れないため
        # phonebookファイルからエントリ名を読み取る
        pbk_paths = []
        appdata = os.environ.get("APPDATA", "")
        programdata = os.environ.get("ProgramData", "")
        if appdata:
            pbk_paths.append(os.path.join(appdata, r"Microsoft\Network\Connections\Pbk\rasphone.pbk"))
        if programdata:
            pbk_paths.append(os.path.join(programdata, r"Microsoft\Network\Connections\Pbk\rasphone.pbk"))

        names = []
        for pbk in pbk_paths:
            if not os.path.exists(pbk):
                continue
            cfg = configparser.ConfigParser(strict=False)
            cfg.read(pbk, encoding="utf-8")
            for section in cfg.sections():
                if section and section not in names:
                    names.append(section)
        if names:
            return names
    except Exception:
        pass

    # フォールバック: PowerShell
    try:
        ps_cmd = (
            "Get-VpnConnection -ErrorAction SilentlyContinue "
            "| Select-Object -ExpandProperty Name; "
            "Get-VpnConnection -AllUserConnection -ErrorAction SilentlyContinue "
            "| Select-Object -ExpandProperty Name"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15
        , creationflags=NOWND)
        seen, unique = set(), []
        for line in result.stdout.splitlines():
            name = line.strip()
            if name and name not in seen:
                seen.add(name)
                unique.append(name)
        return unique
    except Exception:
        return []

def get_vpn_connection_status():
    try:
        ps_cmd = (
            "Get-VpnConnection -ErrorAction SilentlyContinue "
            "| Where-Object {$_.ConnectionStatus -eq 'Connected'} "
            "| Select-Object -ExpandProperty Name; "
            "Get-VpnConnection -AllUserConnection -ErrorAction SilentlyContinue "
            "| Where-Object {$_.ConnectionStatus -eq 'Connected'} "
            "| Select-Object -ExpandProperty Name"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10
        , creationflags=NOWND)
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return lines[0] if lines else None
    except Exception:
        return None

def refresh_vpn_list_ui():
    """バックグラウンドでVPN一覧を取得してリストを更新する（UIが固まらないよう非同期化）"""
    vpn_listbox.delete(0, tk.END)
    vpn_listbox.insert(tk.END, "取得中…")

    def _fetch():
        vpn_list = get_vpn_list()
        def _update():
            vpn_listbox.delete(0, tk.END)
            if vpn_list:
                for name in vpn_list:
                    vpn_listbox.insert(tk.END, name)
                # config.iniに保存済みのVPNを再選択
                config = load_ini()
                saved = config["Settings"].get("vpnname", "")
                if saved in vpn_list:
                    vpn_listbox.selection_set(vpn_list.index(saved))
            else:
                vpn_listbox.insert(tk.END, "（VPN接続が見つかりません）")
        root_ref.after(0, _update)

    threading.Thread(target=_fetch, daemon=True).start()

def toggle_password_visibility():
    if vpn_pass_entry.cget("show") == "*":
        vpn_pass_entry.configure(show="")
        vpn_toggle_btn.configure(text="非表示")
    else:
        vpn_pass_entry.configure(show="*")
        vpn_toggle_btn.configure(text="表示")

def connect_vpn_action():
    selected = vpn_listbox.curselection()
    if not selected:
        messagebox.showwarning("警告", "接続するVPNを選択してください")
        return
    vpn_name = vpn_listbox.get(selected[0])
    if vpn_name == "（VPN接続が見つかりません）":
        messagebox.showwarning("警告", "有効なVPN接続がありません\n「一覧を更新」を押してください")
        return
    username = vpn_user_var.get().strip()
    password = vpn_pass_var.get().strip()
    if not username or not password:
        messagebox.showwarning("警告", "ユーザー名とパスワードを入力してください")
        return
    config = load_ini()
    config["Settings"]["vpnname"] = vpn_name
    config["Settings"]["vpnuser"] = username
    config["Settings"]["vpnpass"] = password
    save_ini(config)
    vpn_status_label.config(text="接続中…", fg="#e07000")

    def do_connect():
        try:
            # RasSetCredentialsW でRASシステムに認証情報を直接登録する。
            # すでに接続済みか確認
            if get_vpn_connection_status() == vpn_name:
                root_ref.after(0, lambda: vpn_status_label.config(
                    text=f"接続中: {vpn_name}", fg="#1a7a1a"))
                root_ref.after(0, lambda: messagebox.showinfo(
                    "情報", f"すでに「{vpn_name}」に接続中です。"))
                return
            # rasphone ダイアログはこの情報を読んでID・PW欄を自動入力する。
            set_ras_credentials(vpn_name, username, password)
            # rasphone -d でVPN接続ダイアログを開く（認証情報入力済み状態）
            subprocess.Popen(["rasphone", "-d", vpn_name])
            root_ref.after(0, lambda: vpn_status_label.config(
                text="ダイアログを開きました", fg="#e07000"))
        except Exception as e:
            root_ref.after(0, lambda: messagebox.showerror(
                "エラー", f"VPN接続中にエラーが発生しました: {e}"))

    threading.Thread(target=do_connect, daemon=True).start()

def disconnect_vpn_action():
    selected = vpn_listbox.curselection()
    if not selected:
        messagebox.showwarning("警告", "切断するVPNを選択してください")
        return
    vpn_name = vpn_listbox.get(selected[0])
    if vpn_name == "（VPN接続が見つかりません）":
        return
    vpn_status_label.config(text="切断中…", fg="#e07000")

    def do_disconnect():
        try:
            result = subprocess.run(
                ["rasdial", vpn_name, "/disconnect"],
                capture_output=True, text=True, timeout=20
            , creationflags=NOWND)
            if result.returncode == 0:
                root_ref.after(0, lambda: vpn_status_label.config(text="未接続", fg="#555555"))
                root_ref.after(0, lambda: messagebox.showinfo("成功", f"VPNを切断しました:\n{vpn_name}"))
            else:
                err = (result.stdout + result.stderr).strip()
                root_ref.after(0, lambda: vpn_status_label.config(text="切断失敗", fg="#cc0000"))
                root_ref.after(0, lambda: messagebox.showerror("エラー", f"VPN切断に失敗しました:\n{err}"))
        except Exception as e:
            root_ref.after(0, lambda: messagebox.showerror("エラー", f"VPN切断中にエラーが発生しました: {e}"))

    threading.Thread(target=do_disconnect, daemon=True).start()

# ─────────────────────────────────────────────────
# Liquid Glass テーマ
# ─────────────────────────────────────────────────


BG        = "#ccddf0"   # ライトブルー（グラデーション背景フォールバック）
PANEL_BG  = "#f0f5ff"   # ほぼ白のガラスパネル
PANEL_BD  = "#aac4e0"   # 薄い青ボーダー
TEXT1     = "#1a2540"   # ダークネイビー（読みやすい）
TEXT2     = "#5570a0"   # ミディアムブルーグレー
BTN_ON    = "#1a7a40"
BTN_ON_H  = "#22943d"
BTN_OFF   = "#b03030"
BTN_OFF_H = "#cc3838"
BTN_NEU   = "#4068b0"   # ブルーガラスボタン
BTN_NEU_H = "#3058a0"
LB_BG     = "#e4eefa"   # 薄い水色リストボックス
LB_SEL    = "#4068b0"
STATUS_OK = "#1a7a40"   # ダークグリーン
STATUS_NG = "#5570a0"   # TEXT2 と同じ
APP_NAME  = "プロキシｸﾝ"


def _draw_gradient(canvas, w, h):
    """グラデーション背景（ライトスカイブルー → ソフトラベンダー）"""
    if w <= 1 or h <= 1:
        return
    canvas.delete("all")
    for y in range(0, h, 2):
        t = y / max(h - 1, 1)
        r = int(0xd0 * (1 - t) + 0xe0 * t)   # d0=208 → e0=224
        g = int(0xe4 * (1 - t) + 0xd4 * t)   # e4=228 → d4=212
        b = int(0xf8 * (1 - t) + 0xf8 * t)   # f8=248 → f8=248（青みを保持）
        canvas.create_line(0, y, w, y + 1, fill=f"#{r:02x}{g:02x}{b:02x}")


def _status_lbl(parent, text, fg=None):
    """ビジネスロジックから .config(text=, fg=) で更新できる tk.Label"""
    lbl = tk.Label(parent, text=text,
                   bg=PANEL_BG, fg=fg or STATUS_NG,
                   font=("Meiryo UI", 11, "bold"), anchor="w")
    lbl.pack(fill=tk.X, padx=16, pady=(6, 2))
    return lbl


def _make_lb(parent, height=3):
    """Listbox を CTkFrame でラップして返す"""
    frame = ctk.CTkFrame(parent, fg_color=LB_BG,
                         corner_radius=10,
                         border_width=1, border_color=PANEL_BD)
    lb = tk.Listbox(frame,
                    selectmode=tk.SINGLE,
                    width=42, height=max(len(PROXY_LIST), height),
                    bg=LB_BG, fg=TEXT1,
                    selectbackground=LB_SEL, selectforeground="#ffffff",
                    activestyle="none", relief="flat", bd=0,
                    font=("Meiryo UI", 11),
                    highlightthickness=0)
    lb.pack(padx=6, pady=6, fill=tk.X)
    frame.pack(pady=(2, 8), fill=tk.X, padx=14)
    return lb


def _btn_row(parent, l_txt, l_cmd, r_txt, r_cmd):
    """ピル形のボタン 2 つを並べる行"""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(pady=(2, 14))
    ctk.CTkButton(row, text=l_txt, command=l_cmd,
                  fg_color=BTN_ON, hover_color=BTN_ON_H,
                  corner_radius=18, height=32, width=155,
                  font=ctk.CTkFont("Meiryo UI", 10, "bold")).pack(side=tk.LEFT, padx=6)
    ctk.CTkButton(row, text=r_txt, command=r_cmd,
                  fg_color=BTN_OFF, hover_color=BTN_OFF_H,
                  corner_radius=18, height=32, width=155,
                  font=ctk.CTkFont("Meiryo UI", 10, "bold")).pack(side=tk.LEFT, padx=6)


def _section(parent, key, title):
    """フロストガラスパネル"""
    f = ctk.CTkFrame(parent,
                     fg_color=PANEL_BG,
                     corner_radius=22,
                     border_width=1,
                     border_color=PANEL_BD)
    ctk.CTkLabel(f, text=title,
                 text_color=TEXT1,
                 font=ctk.CTkFont("Meiryo UI", 11, "bold")).pack(
                     anchor="w", padx=16, pady=(14, 4))
    section_frames[key] = f
    return f


# ─────────────────────────────────────────────────
# 表示設定ダイアログ
# ─────────────────────────────────────────────────

def open_visibility_settings():
    dialog = ctk.CTkToplevel(root_ref)
    dialog.title("表示設定")
    dialog.configure(fg_color=PANEL_BG)
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.after(60, dialog.focus_set)

    ctk.CTkLabel(dialog, text="SECTIONS",
                 text_color=TEXT2,
                 font=ctk.CTkFont("Meiryo UI", 10, "bold")).pack(
                     padx=24, pady=(16, 8), anchor="w")

    for key, label in SECTION_KEYS:
        ctk.CTkCheckBox(
            dialog, text=label,
            variable=visibility_vars[key],
            command=apply_visibility,
            text_color=TEXT1,
            fg_color=BTN_NEU_H,
            hover_color=BTN_NEU,
            checkmark_color="#ffffff",
            font=ctk.CTkFont("Meiryo UI", 10),
        ).pack(padx=24, pady=3, anchor="w")

    ctk.CTkButton(dialog, text="閉じる",
                  command=dialog.destroy,
                  fg_color=BTN_NEU, hover_color=BTN_NEU_H,
                  corner_radius=16, height=32, width=110,
                  font=ctk.CTkFont("Meiryo UI", 10, "bold")).pack(pady=(14, 18))


# ─────────────────────────────────────────────────
# スプラッシュ・メインウィンドウ
# ─────────────────────────────────────────────────

def show_splash(root):
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg=BG)
    splash.attributes("-topmost", True)
    w, h = 300, 120
    sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    inner = tk.Frame(splash, bg=PANEL_BG,
                     highlightbackground=PANEL_BD, highlightthickness=2)
    inner.place(relx=0, rely=0, relwidth=1, relheight=1)
    tk.Label(inner, text=APP_NAME,
             font=("Meiryo UI", 22, "bold"),
             bg=PANEL_BG, fg=TEXT1).pack(expand=True, pady=(22, 4))
    tk.Label(inner, text="読み込み中…",
             font=("Meiryo UI", 10),
             bg=PANEL_BG, fg=TEXT2).pack(pady=(0, 18))
    splash.update()
    return splash



def create_gui():
    global root_ref
    global system_status_label, listbox
    global npm_status_label, npm_listbox
    global env_status_label, env_listbox
    global mgmt_listbox, entry_var
    global bat_label
    global vpn_status_label, vpn_listbox
    global vpn_user_var, vpn_pass_var, vpn_pass_entry, vpn_toggle_btn

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root_ref = root
    root.title(APP_NAME)
    root.configure(fg_color=BG)
    root.geometry("520x760")
    root.minsize(480, 500)
    root.withdraw()
    # アイコン設定（CTk初期化完了後に適用）
    ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    if os.path.exists(ico_path):
        root.after(100, lambda: root.iconbitmap(ico_path))

    splash = show_splash(root)
    load_proxy_list()
    config = load_ini()
    load_visibility(config)

    # ── ヘッダー ──────────────────────────────────
    header = ctk.CTkFrame(root, fg_color=PANEL_BG,
                          corner_radius=0, height=50)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    ctk.CTkLabel(header, text=APP_NAME,
                 font=ctk.CTkFont("Meiryo UI", 17, "bold"),
                 text_color=TEXT1).pack(side=tk.LEFT, padx=20)
    ctk.CTkButton(header, text="⚙  表示設定",
                  command=open_visibility_settings,
                  fg_color=BTN_NEU, hover_color=BTN_NEU_H,
                  text_color="#ffffff",
                  corner_radius=16, height=30, width=112,
                  font=ctk.CTkFont("Meiryo UI", 10, "bold")).pack(
                      side=tk.RIGHT, padx=14)

    # 区切り線
    ctk.CTkFrame(root, fg_color=PANEL_BD,
                 height=1, corner_radius=0).pack(fill=tk.X)

    # ── スクロール可能なコンテンツエリア ──────────
    scroll = ctk.CTkScrollableFrame(root, fg_color=BG, corner_radius=0)
    scroll.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

    def make_section(key, title):
        return _section(scroll, key, title)

    # ── システムプロキシ ──────────────────────────
    proxy_sec = make_section("systemproxy", "システムプロキシ")
    cur = get_system_proxy_status()
    system_status_label = _status_lbl(
        proxy_sec,
        f"現在: {cur}" if cur else "現在: 無効",
        fg=STATUS_OK if cur else STATUS_NG)
    listbox = _make_lb(proxy_sec)
    for p in PROXY_LIST:
        listbox.insert(tk.END, p)
    _btn_row(proxy_sec,
             "プロキシを設定", set_system_proxy,
             "プロキシを無効化", disable_system_proxy)

    # ── npm プロキシ ──────────────────────────────
    npm_sec = make_section("npmproxy", "npm プロキシ")
    cur = get_npm_proxy_status()
    npm_status_label = _status_lbl(
        npm_sec,
        f"現在: {cur}" if cur else "現在: 無効",
        fg=STATUS_OK if cur else STATUS_NG)
    npm_listbox = _make_lb(npm_sec)
    for p in PROXY_LIST:
        npm_listbox.insert(tk.END, p)
    _btn_row(npm_sec,
             "npm プロキシ ON", set_npm_proxy,
             "npm プロキシ OFF", disable_npm_proxy)

    # ── 環境変数プロキシ ──────────────────────────
    env_sec = make_section("envproxy", "環境変数プロキシ  (Claude Code用)")
    cur = get_env_proxy_status()
    env_status_label = _status_lbl(
        env_sec,
        f"現在: {cur}" if cur else "現在: 無効",
        fg=STATUS_OK if cur else STATUS_NG)
    env_listbox = _make_lb(env_sec)
    for p in PROXY_LIST:
        env_listbox.insert(tk.END, p)
    _btn_row(env_sec,
             "環境変数 ON", set_env_proxy,
             "環境変数 OFF", disable_env_proxy)

    # ── IP リスト管理 ─────────────────────────────
    mgmt_sec = make_section("iplist", "IP リスト管理")
    entry_var = tk.StringVar()
    erow = ctk.CTkFrame(mgmt_sec, fg_color="transparent")
    erow.pack(fill=tk.X, padx=14, pady=(4, 4))
    ctk.CTkLabel(erow, text="追加:", text_color=TEXT2,
                 font=ctk.CTkFont("Meiryo UI", 10)).pack(side=tk.LEFT)
    ctk.CTkEntry(erow, textvariable=entry_var, width=200,
                 fg_color=LB_BG, border_color=PANEL_BD,
                 text_color=TEXT1, corner_radius=10,
                 placeholder_text="172.20.1.1:8080",
                 font=ctk.CTkFont("Meiryo UI", 10)).pack(
                     side=tk.LEFT, padx=8)
    mgmt_listbox = _make_lb(mgmt_sec)
    for p in PROXY_LIST:
        mgmt_listbox.insert(tk.END, p)
    _btn_row(mgmt_sec, "追加", add_proxy, "削除", remove_proxy)

    # ── VPN 接続 ──────────────────────────────────
    vpn_sec = make_section("vpn", "VPN 接続")
    vrow = ctk.CTkFrame(vpn_sec, fg_color="transparent")
    vrow.pack(fill=tk.X, padx=14, pady=(4, 4))
    cur = get_vpn_connection_status()
    vpn_status_label = tk.Label(
        vrow,
        text=f"接続中: {cur}" if cur else "現在: 未接続",
        anchor="w", bg=PANEL_BG,
        fg=STATUS_OK if cur else STATUS_NG,
        font=("Meiryo UI", 11, "bold"),
        cursor="arrow")
    vpn_status_label.pack(side=tk.LEFT)
    ctk.CTkButton(vrow, text="一覧を更新",
                  command=refresh_vpn_list_ui,
                  fg_color=BTN_NEU, hover_color=BTN_NEU_H,
                  text_color="#ffffff",
                  corner_radius=14, height=28, width=95,
                  font=ctk.CTkFont("Meiryo UI", 10, "bold")).pack(side=tk.RIGHT)

    vpn_list = get_vpn_list()
    vpn_lb_f = ctk.CTkFrame(vpn_sec, fg_color=LB_BG,
                             corner_radius=10,
                             border_width=1, border_color=PANEL_BD)
    vpn_listbox = tk.Listbox(
        vpn_lb_f,
        selectmode=tk.SINGLE,
        width=42, height=max(len(vpn_list) if vpn_list else 1, 3),
        bg=LB_BG, fg=TEXT1,
        selectbackground=LB_SEL, selectforeground="#ffffff",
        activestyle="none", relief="flat", bd=0,
        font=("Meiryo UI", 11), highlightthickness=0)
    if vpn_list:
        for name in vpn_list:
            vpn_listbox.insert(tk.END, name)
    else:
        vpn_listbox.insert(tk.END, "（VPN接続が見つかりません）")
    vpn_listbox.pack(padx=5, pady=5, fill=tk.X)
    vpn_lb_f.pack(pady=(2, 8), fill=tk.X, padx=14)

    saved = config["Settings"].get("vpnname", "")
    if saved in vpn_list:
        vpn_listbox.selection_set(vpn_list.index(saved))

    def _inp(parent, label_text, var, show=""):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, padx=14, pady=(0, 4))
        ctk.CTkLabel(row, text=label_text, width=84, anchor="w",
                     text_color=TEXT2,
                     font=ctk.CTkFont("Meiryo UI", 10)).pack(side=tk.LEFT)
        e = ctk.CTkEntry(row, textvariable=var, show=show, width=200,
                         fg_color=LB_BG, border_color=PANEL_BD,
                         text_color=TEXT1, corner_radius=10,
                         font=ctk.CTkFont("Meiryo UI", 10))
        e.pack(side=tk.LEFT, padx=6)
        return e

    vpn_user_var = tk.StringVar(value=config["Settings"].get("vpnuser", ""))
    _inp(vpn_sec, "ユーザー名:", vpn_user_var)

    vpn_pass_var = tk.StringVar(value=config["Settings"].get("vpnpass", ""))
    prow = ctk.CTkFrame(vpn_sec, fg_color="transparent")
    prow.pack(fill=tk.X, padx=14, pady=(0, 6))
    ctk.CTkLabel(prow, text="パスワード:", width=84, anchor="w",
                 text_color=TEXT2,
                 font=ctk.CTkFont("Meiryo UI", 10)).pack(side=tk.LEFT)
    vpn_pass_entry = ctk.CTkEntry(
        prow, textvariable=vpn_pass_var, show="*", width=200,
        fg_color=LB_BG, border_color=PANEL_BD,
        text_color=TEXT1, corner_radius=10,
        font=ctk.CTkFont("Meiryo UI", 10))
    vpn_pass_entry.pack(side=tk.LEFT, padx=6)
    vpn_toggle_btn = ctk.CTkButton(
        prow, text="表示",
        command=toggle_password_visibility,
        fg_color=BTN_NEU, hover_color=BTN_NEU_H,
        text_color="#ffffff",
        corner_radius=12, height=28, width=62,
        font=ctk.CTkFont("Meiryo UI", 10, "bold"))
    vpn_toggle_btn.pack(side=tk.LEFT)
    _btn_row(vpn_sec, "接続", connect_vpn_action, "切断", disconnect_vpn_action)

    # ── BAT ファイル ──────────────────────────────
    bat_sec = make_section("batfile", "BAT ファイル")
    bat_path = config["Settings"].get("batpath", "")
    bat_label = tk.Label(
        bat_sec,
        text=("\u8a2d\u5b9a: " + bat_path) if bat_path else "BAT \u30d5\u30a1\u30a4\u30eb\u304c\u8a2d\u5b9a\u3055\u308c\u3066\u3044\u307e\u305b\u3093",
        wraplength=360, anchor="w",
        bg=PANEL_BG, fg=TEXT2,
        font=("Meiryo UI", 11), justify="left")
    bat_label.pack(fill=tk.X, padx=16, pady=(4, 0))
    _btn_row(bat_sec,
             "\u30d5\u30a1\u30a4\u30eb\u3092\u9078\u629e", select_bat_file,
             "\u30d5\u30a1\u30a4\u30eb\u3092\u5b9f\u884c", run_bat_file)

    # \u2500\u2500 \u521d\u671f\u8868\u793a \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    apply_visibility()
    splash.destroy()
    root.after(20, root.deiconify)
    root.after(30, root.lift)
    root.after(30, root.focus_force)
    root.mainloop()


if __name__ == "__main__":
    try:
        create_gui()
    except Exception:
        import traceback
        err = traceback.format_exc()
        with open("error.log", "w", encoding="utf-8") as _f:
            _f.write(err)
        try:
            _r = tk.Tk()
            _r.withdraw()
            messagebox.showerror("起動エラー", err)
            _r.destroy()
        except Exception:
            pass
