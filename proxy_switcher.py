import winreg
import ctypes
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import configparser
import threading
import os

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
    PACK_OPTS = dict(pady=6, fill=tk.X)
    for key, _ in SECTION_KEYS:
        frame = section_frames.get(key)
        if frame:
            frame.pack_forget()
    for key, _ in SECTION_KEYS:
        frame = section_frames.get(key)
        if frame and visibility_vars[key].get():
            frame.pack(**PACK_OPTS)
    # ウィンドウサイズをコンテンツに合わせて自動調整
    root_ref.update_idletasks()
    root_ref.geometry("")
    save_visibility()

def open_visibility_settings():
    """表示設定ダイアログを開く"""
    dialog = tk.Toplevel(root_ref)
    dialog.title("表示設定")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.focus_set()

    tk.Label(dialog, text="表示するセクションを選択してください",
             font=("", 9), pady=6).pack(padx=20, anchor="w")

    for key, label in SECTION_KEYS:
        tk.Checkbutton(
            dialog, text=label,
            variable=visibility_vars[key],
            command=apply_visibility,
            anchor="w", width=30
        ).pack(padx=20, pady=2, anchor="w")

    tk.Button(dialog, text="閉じる", command=dialog.destroy,
              width=12).pack(pady=10)

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
                                capture_output=True, text=True, timeout=5, shell=True)
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
        subprocess.run(f"npm config set proxy {proxy_url}", check=True, timeout=10, shell=True)
        subprocess.run(f"npm config set https-proxy {proxy_url}", check=True, timeout=10, shell=True)
        npm_status_label.config(text=f"現在: {proxy_url}")
        messagebox.showinfo("成功", f"npmプロキシを設定しました:\n{proxy_url}")
    except FileNotFoundError:
        messagebox.showerror("エラー", "npmが見つかりません。")
    except Exception as e:
        messagebox.showerror("エラー", f"npmプロキシ設定中にエラーが発生しました: {e}")

def disable_npm_proxy():
    try:
        subprocess.run("npm config delete proxy", check=True, timeout=10, shell=True)
        subprocess.run("npm config delete https-proxy", check=True, timeout=10, shell=True)
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
        )
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
        )
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
        vpn_pass_entry.config(show="")
        vpn_toggle_btn.config(text="非表示")
    else:
        vpn_pass_entry.config(show="*")
        vpn_toggle_btn.config(text="表示")

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
            )
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
# GUI 構築
# ─────────────────────────────────────────────────

def create_gui():
    global root_ref
    global system_status_label, listbox
    global npm_status_label, npm_listbox
    global env_status_label, env_listbox
    global mgmt_listbox, entry_var
    global bat_label
    global vpn_status_label, vpn_listbox
    global vpn_user_var, vpn_pass_var, vpn_pass_entry, vpn_toggle_btn

    load_proxy_list()
    config = load_ini()

    root = tk.Tk()
    root_ref = root
    root.title("プロキシｸﾝ")

    # 表示設定を読み込む（BooleanVarはroot生成後に作る必要あり）
    load_visibility(config)

    # ─── ヘッダー（表示設定ボタン）───────────────
    header = tk.Frame(root, padx=12, pady=4, bg="#f0f0f0")
    header.pack(fill=tk.X)
    tk.Label(header, text="プロキシｸﾝ", font=("", 11, "bold"),
             bg="#f0f0f0").pack(side=tk.LEFT)
    tk.Button(header, text="⚙ 表示設定",
              command=open_visibility_settings,
              relief="flat", bg="#d8d8d8", activebackground="#c0c0c0",
              padx=8).pack(side=tk.RIGHT)

    tk.Frame(root, height=1, bg="#cccccc").pack(fill=tk.X)  # 区切り線

    main_frame = tk.Frame(root, padx=12, pady=8)
    main_frame.pack(fill=tk.BOTH, expand=True)

    BTN_W = 18

    def make_section(key, title):
        f = tk.LabelFrame(main_frame, text=f"  {title}  ", padx=10, pady=8,
                          font=("", 9, "bold"))
        section_frames[key] = f
        return f

    def make_listbox(parent):
        lb = tk.Listbox(parent, selectmode=tk.SINGLE, width=46,
                        height=max(len(PROXY_LIST), 2),
                        activestyle="dotbox", relief="solid", bd=1)
        for proxy in PROXY_LIST:
            lb.insert(tk.END, proxy)
        lb.pack(pady=(4, 6))
        return lb

    def make_btn_row(parent, left_text, left_cmd, right_text, right_cmd):
        row = tk.Frame(parent)
        row.pack(pady=(0, 4))
        tk.Button(row, text=left_text, command=left_cmd, width=BTN_W,
                  bg="#c3e6cb", activebackground="#a3d9a5").pack(side=tk.LEFT, padx=6)
        tk.Button(row, text=right_text, command=right_cmd, width=BTN_W,
                  bg="#f5c6cb", activebackground="#e09ba1").pack(side=tk.LEFT, padx=6)

    def make_status(parent, text, fg="#555555"):
        lbl = tk.Label(parent, text=text, anchor="w", fg=fg)
        lbl.pack(fill=tk.X, pady=(0, 2))
        return lbl

    # ── システムプロキシ ──────────────────────────
    proxy_sec = make_section("systemproxy", "システムプロキシ")
    current_system = get_system_proxy_status()
    system_status_label = make_status(proxy_sec,
        f"現在: {current_system}" if current_system else "現在: 無効")
    listbox = make_listbox(proxy_sec)
    make_btn_row(proxy_sec, "プロキシを設定", set_system_proxy,
                 "プロキシを無効化", disable_system_proxy)

    # ── npm プロキシ ──────────────────────────────
    npm_sec = make_section("npmproxy", "npm プロキシ")
    current_npm = get_npm_proxy_status()
    npm_status_label = make_status(npm_sec,
        f"現在: {current_npm}" if current_npm else "現在: 無効")
    npm_listbox = make_listbox(npm_sec)
    make_btn_row(npm_sec, "npm プロキシ ON", set_npm_proxy,
                 "npm プロキシ OFF", disable_npm_proxy)

    # ── 環境変数プロキシ ──────────────────────────
    env_sec = make_section("envproxy", "環境変数プロキシ  (Claude Code用)")
    current_env = get_env_proxy_status()
    env_status_label = make_status(env_sec,
        f"現在: {current_env}" if current_env else "現在: 無効")
    env_listbox = make_listbox(env_sec)
    make_btn_row(env_sec, "環境変数 ON", set_env_proxy,
                 "環境変数 OFF", disable_env_proxy)

    # ── IPリスト管理 ──────────────────────────────
    mgmt_sec = make_section("iplist", "IPリスト管理")
    entry_var = tk.StringVar()
    entry_row = tk.Frame(mgmt_sec)
    entry_row.pack(fill=tk.X, pady=(0, 4))
    tk.Label(entry_row, text="追加:").pack(side=tk.LEFT)
    tk.Entry(entry_row, textvariable=entry_var, width=28).pack(side=tk.LEFT, padx=6)
    tk.Label(entry_row, text="例: 172.20.1.1:8080", fg="#888888").pack(side=tk.LEFT)
    mgmt_listbox = make_listbox(mgmt_sec)
    add_row = tk.Frame(mgmt_sec)
    add_row.pack(pady=(0, 4))
    tk.Button(add_row, text="追加", command=add_proxy, width=BTN_W,
              bg="#c3e6cb", activebackground="#a3d9a5").pack(side=tk.LEFT, padx=6)
    tk.Button(add_row, text="削除", command=remove_proxy, width=BTN_W,
              bg="#f5c6cb", activebackground="#e09ba1").pack(side=tk.LEFT, padx=6)

    # ── VPN 接続 ──────────────────────────────────
    vpn_sec = make_section("vpn", "VPN 接続")
    vpn_top_row = tk.Frame(vpn_sec)
    vpn_top_row.pack(fill=tk.X, pady=(0, 4))
    current_vpn = get_vpn_connection_status()
    vpn_status_label = tk.Label(vpn_top_row,
        text=f"接続中: {current_vpn}" if current_vpn else "現在: 未接続",
        anchor="w", fg="#1a7a1a" if current_vpn else "#555555")
    vpn_status_label.pack(side=tk.LEFT)
    tk.Button(vpn_top_row, text="一覧を更新", command=refresh_vpn_list_ui,
              width=10).pack(side=tk.RIGHT)
    vpn_list = get_vpn_list()
    vpn_listbox = tk.Listbox(vpn_sec, selectmode=tk.SINGLE, width=46,
                              height=max(len(vpn_list), 3),
                              activestyle="dotbox", relief="solid", bd=1)
    if vpn_list:
        for name in vpn_list:
            vpn_listbox.insert(tk.END, name)
    else:
        vpn_listbox.insert(tk.END, "（VPN接続が見つかりません）")
    vpn_listbox.pack(pady=(0, 6))
    saved_vpn_name = config["Settings"].get("vpnname", "")
    if saved_vpn_name in vpn_list:
        vpn_listbox.selection_set(vpn_list.index(saved_vpn_name))
    user_row = tk.Frame(vpn_sec)
    user_row.pack(fill=tk.X, pady=(0, 4))
    tk.Label(user_row, text="ユーザー名:", width=11, anchor="w").pack(side=tk.LEFT)
    vpn_user_var = tk.StringVar(value=config["Settings"].get("vpnuser", ""))
    tk.Entry(user_row, textvariable=vpn_user_var, width=28).pack(side=tk.LEFT, padx=6)
    pass_row = tk.Frame(vpn_sec)
    pass_row.pack(fill=tk.X, pady=(0, 6))
    tk.Label(pass_row, text="パスワード:", width=11, anchor="w").pack(side=tk.LEFT)
    vpn_pass_var = tk.StringVar(value=config["Settings"].get("vpnpass", ""))
    vpn_pass_entry = tk.Entry(pass_row, textvariable=vpn_pass_var, show="*", width=28)
    vpn_pass_entry.pack(side=tk.LEFT, padx=6)
    vpn_toggle_btn = tk.Button(pass_row, text="表示", width=6,
                                command=toggle_password_visibility)
    vpn_toggle_btn.pack(side=tk.LEFT)
    make_btn_row(vpn_sec, "接続", connect_vpn_action, "切断", disconnect_vpn_action)

    # ── BAT ファイル ──────────────────────────────
    bat_sec = make_section("batfile", "BAT ファイル")
    bat_path = config["Settings"].get("batpath", "")
    bat_label = tk.Label(bat_sec,
                         text=("設定: " + bat_path) if bat_path else "batファイルが設定されていません",
                         wraplength=400, anchor="w", fg="#555555", justify="left")
    bat_label.pack(fill=tk.X, pady=(0, 4))
    make_btn_row(bat_sec, "ファイルを選択", select_bat_file,
                 "ファイルを実行", run_bat_file)

    # ── 初期表示を適用 ────────────────────────────
    apply_visibility()

    root.mainloop()

if __name__ == "__main__":
    create_gui()
