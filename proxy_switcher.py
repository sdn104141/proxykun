# import winreg
# import ctypes
# import tkinter as tk
# from tkinter import messagebox

# # プロキシリスト
# PROXY_LIST = [
#     "172.20.15.153:8080",
#     "172.20.4.3:8080",
# ]

# # システムプロキシを設定する関数
# def set_system_proxy():
#     try:
#         selected = listbox.curselection()
#         if not selected:
#             messagebox.showwarning("警告", "プロキシを選択してください")
#             return

#         proxy_address = PROXY_LIST[selected[0]]

#         # レジストリにプロキシ設定を反映
#         key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_SET_VALUE)
#         winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
#         winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_address)
#         winreg.CloseKey(key)

#         # 設定を適用
#         ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
#         ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)

#         messagebox.showinfo("成功", f"プロキシを設定しました:\n{proxy_address}")
#     except Exception as e:
#         messagebox.showerror("エラー", f"プロキシ設定中にエラーが発生しました: {e}")

# # プロキシを無効にする関数
# def disable_system_proxy():
#     try:
#         key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_SET_VALUE)
#         winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
#         winreg.CloseKey(key)

#         ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
#         ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)

#         messagebox.showinfo("成功", "プロキシを無効にしました")
#     except Exception as e:
#         messagebox.showerror("エラー", f"プロキシ無効化中にエラーが発生しました: {e}")

# # GUIの作成
# def create_gui():
#     root = tk.Tk()
#     root.title("プロキシｸﾝ")
#     root.geometry("400x300")

#     label = tk.Label(root, text="プロキシを選択してください:")
#     label.pack(pady=10)

#     global listbox
#     listbox = tk.Listbox(root, selectmode=tk.SINGLE, width=50, height=10)
#     for proxy in PROXY_LIST:
#         listbox.insert(tk.END, proxy)
#     listbox.pack(pady=10)

#     set_button = tk.Button(root, text="プロキシを設定", command=set_system_proxy, width=20)
#     set_button.pack(pady=5)

#     disable_button = tk.Button(root, text="プロキシを無効化", command=disable_system_proxy, width=20)
#     disable_button.pack(pady=5)

#     root.mainloop()

# if __name__ == "__main__":
#     create_gui()

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

# 現在のシステムプロキシ設定をレジストリから取得する関数
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

# システムプロキシを設定する関数
def set_system_proxy():
    try:
        selected = listbox.curselection()
        if not selected:
            messagebox.showwarning("警告", "プロキシを選択してください")
            return

        proxy_address = PROXY_LIST[selected[0]]

        # レジストリにプロキシ設定を反映
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_address)
        winreg.CloseKey(key)

        # 設定を適用
        ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
        ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)

        system_status_label.config(text=f"現在: {proxy_address}")
        messagebox.showinfo("成功", f"プロキシを設定しました:\n{proxy_address}")
    except Exception as e:
        messagebox.showerror("エラー", f"プロキシ設定中にエラーが発生しました: {e}")

# プロキシを無効にする関数
def disable_system_proxy():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)

        ctypes.windll.wininet.InternetSetOptionW(0, 37, 0, 0)
        ctypes.windll.wininet.InternetSetOptionW(0, 39, 0, 0)

        system_status_label.config(text="現在: 無効")
        messagebox.showinfo("成功", "プロキシを無効にしました")
    except Exception as e:
        messagebox.showerror("エラー", f"プロキシ無効化中にエラーが発生しました: {e}")

# iniファイルを読み込む関数
def load_ini():
    config = configparser.ConfigParser()
    config.read(INI_FILE_PATH, encoding="utf-8")
    if "Settings" not in config:
        config["Settings"] = {"batPath": ""}
    return config

# iniファイルに書き込む関数
def save_ini(config):
    with open(INI_FILE_PATH, "w", encoding="utf-8") as configfile:
        config.write(configfile)

# プロキシリストをiniから読み込む関数
def load_proxy_list():
    global PROXY_LIST
    config = load_ini()
    raw = config["Settings"].get("proxylist", "")
    if raw.strip():
        PROXY_LIST = [p.strip() for p in raw.split(",") if p.strip()]
    else:
        PROXY_LIST = list(DEFAULT_PROXY_LIST)

# プロキシリストをiniに保存する関数
def save_proxy_list():
    config = load_ini()
    config["Settings"]["proxylist"] = ",".join(PROXY_LIST)
    save_ini(config)

# 全リストボックスをリフレッシュする関数
def refresh_all_listboxes():
    for lb in (listbox, npm_listbox, env_listbox, mgmt_listbox):
        lb.delete(0, tk.END)
        for proxy in PROXY_LIST:
            lb.insert(tk.END, proxy)

# プロキシを追加する関数
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

# プロキシを削除する関数
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

# batファイルを実行する関数
def run_bat_file():
    try:
        config = load_ini()
        bat_path = config["Settings"].get("batPath", "")
        if not bat_path:
            messagebox.showwarning("警告", "batファイルが設定されていません")
            return

        # batファイルを別スレッドで実行
        threading.Thread(target=execute_bat, args=(bat_path,)).start()
    except Exception as e:
        messagebox.showerror("エラー", f"batファイル実行中にエラーが発生しました: {e}")

# batファイルを実際に実行する関数（スレッド内で呼び出される）
def execute_bat(bat_path):
    try:
        # batファイルのフルパスを取得
        if not os.path.isabs(bat_path):
            bat_path = os.path.abspath(bat_path)  # 絶対パスに変換

        if not os.path.exists(bat_path):
            messagebox.showerror("エラー", f"指定されたbatファイルが存在しません: {bat_path}")
            return

        # 新しいコマンドプロンプトウィンドウでbatファイルを実行
        subprocess.call(
            f"start cmd /K \"{bat_path}\"", 
            shell=True
        )

    except Exception as e:
        messagebox.showerror("エラー", f"batファイル実行中にエラーが発生しました: {e}")

# 現在のnpmプロキシ設定を取得する関数
def get_npm_proxy_status():
    try:
        result = subprocess.run(
            "npm config get proxy",
            capture_output=True, text=True, timeout=5, shell=True
        )
        value = result.stdout.strip()
        return value if value and value != "null" else None
    except Exception:
        return None

# npmプロキシを設定する関数
def set_npm_proxy():
    try:
        selected = npm_listbox.curselection()
        if not selected:
            messagebox.showwarning("警告", "プロキシを選択してください")
            return

        proxy_address = PROXY_LIST[selected[0]]
        proxy_url = f"http://{proxy_address}"

        subprocess.run(f"npm config set proxy {proxy_url}", check=True, timeout=10, shell=True)
        subprocess.run(f"npm config set https-proxy {proxy_url}", check=True, timeout=10, shell=True)

        npm_status_label.config(text=f"npm プロキシ: {proxy_url}")
        messagebox.showinfo("成功", f"npmプロキシを設定しました:\n{proxy_url}")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("エラー", f"npmプロキシ設定中にエラーが発生しました: {e}")
    except FileNotFoundError:
        messagebox.showerror("エラー", "npmが見つかりません。npmがインストールされているか確認してください。")
    except Exception as e:
        messagebox.showerror("エラー", f"npmプロキシ設定中にエラーが発生しました: {e}")

# npmプロキシを無効にする関数
def disable_npm_proxy():
    try:
        subprocess.run("npm config delete proxy", check=True, timeout=10, shell=True)
        subprocess.run("npm config delete https-proxy", check=True, timeout=10, shell=True)

        npm_status_label.config(text="npm プロキシ: 無効")
        messagebox.showinfo("成功", "npmプロキシを無効にしました")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("エラー", f"npmプロキシ無効化中にエラーが発生しました: {e}")
    except FileNotFoundError:
        messagebox.showerror("エラー", "npmが見つかりません。npmがインストールされているか確認してください。")
    except Exception as e:
        messagebox.showerror("エラー", f"npmプロキシ無効化中にエラーが発生しました: {e}")

# 現在の環境変数プロキシ設定をレジストリから取得する関数
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

# 環境変数プロキシを設定する関数
def set_env_proxy():
    try:
        selected = env_listbox.curselection()
        if not selected:
            messagebox.showwarning("警告", "プロキシを選択してください")
            return

        proxy_address = PROXY_LIST[selected[0]]
        proxy_url = f"http://{proxy_address}"

        subprocess.run(f'setx HTTP_PROXY "{proxy_url}"', check=True, shell=True, timeout=10)
        subprocess.run(f'setx HTTPS_PROXY "{proxy_url}"', check=True, shell=True, timeout=10)
        subprocess.run('setx NODE_USE_ENV_PROXY 1', check=True, shell=True, timeout=10)

        env_status_label.config(text=f"環境変数プロキシ: {proxy_url}")
        messagebox.showinfo("成功", f"環境変数プロキシを設定しました:\n{proxy_url}\n\n※新しいターミナルを開いてから有効になります")
    except Exception as e:
        messagebox.showerror("エラー", f"環境変数プロキシ設定中にエラーが発生しました: {e}")

# 環境変数プロキシを無効にする関数
def disable_env_proxy():
    try:
        subprocess.run('setx HTTP_PROXY ""', check=True, shell=True, timeout=10)
        subprocess.run('setx HTTPS_PROXY ""', check=True, shell=True, timeout=10)

        env_status_label.config(text="環境変数プロキシ: 無効")
        messagebox.showinfo("成功", "環境変数プロキシを無効にしました\n\n※新しいターミナルを開いてから有効になります")
    except Exception as e:
        messagebox.showerror("エラー", f"環境変数プロキシ無効化中にエラーが発生しました: {e}")

# batファイルを選択する関数
def select_bat_file():
    try:
        file_path = filedialog.askopenfilename(
            title="batファイルを選択",
            filetypes=[("BATファイル", "*.bat")],
        )
        if not file_path:
            return

        # iniファイルに選択したパスを保存
        config = load_ini()
        config["Settings"]["batPath"] = file_path
        save_ini(config)
        bat_label.config(text=f"設定されたbatファイル: {file_path}")
        messagebox.showinfo("成功", "batファイルのパスを設定しました")
    except Exception as e:
        messagebox.showerror("エラー", f"batファイル選択中にエラーが発生しました: {e}")

# GUIの作成
def create_gui():
    load_proxy_list()

    root = tk.Tk()
    root.title("プロキシｸﾝ")
    root.geometry("460x680")
    root.resizable(False, True)

    # スクロール可能なメインエリア
    canvas = tk.Canvas(root, highlightthickness=0)
    scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    main_frame = tk.Frame(canvas, padx=12, pady=8)
    canvas_win = canvas.create_window((0, 0), window=main_frame, anchor="nw")

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_canvas_configure(event):
        canvas.itemconfig(canvas_win, width=event.width)

    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    main_frame.bind("<Configure>", on_frame_configure)
    canvas.bind("<Configure>", on_canvas_configure)
    canvas.bind_all("<MouseWheel>", on_mousewheel)

    SECTION = dict(pady=6, fill=tk.X)
    BTN_W = 18

    def make_section(parent, title):
        f = tk.LabelFrame(parent, text=f"  {title}  ", padx=10, pady=8,
                          font=("", 9, "bold"))
        f.pack(**SECTION)
        return f

    def make_listbox(parent, height=4):
        lb = tk.Listbox(parent, selectmode=tk.SINGLE, width=46, height=height,
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

    def make_status(parent, text):
        lbl = tk.Label(parent, text=text, anchor="w", fg="#555555")
        lbl.pack(fill=tk.X, pady=(0, 2))
        return lbl

    # ── システムプロキシ ──────────────────────────
    proxy_sec = make_section(main_frame, "システムプロキシ")
    global system_status_label, listbox
    current_system = get_system_proxy_status()
    system_status_label = make_status(proxy_sec, f"現在: {current_system}" if current_system else "現在: 無効")
    listbox = make_listbox(proxy_sec)
    make_btn_row(proxy_sec, "プロキシを設定", set_system_proxy,
                 "プロキシを無効化", disable_system_proxy)

    # ── npm プロキシ ──────────────────────────────
    npm_sec = make_section(main_frame, "npm プロキシ")
    global npm_status_label, npm_listbox
    current_npm = get_npm_proxy_status()
    npm_status_label = make_status(npm_sec, f"現在: {current_npm}" if current_npm else "現在: 無効")
    npm_listbox = make_listbox(npm_sec)
    make_btn_row(npm_sec, "npm プロキシ ON", set_npm_proxy,
                 "npm プロキシ OFF", disable_npm_proxy)

    # ── 環境変数プロキシ（Claude Code用）──────────
    env_sec = make_section(main_frame, "環境変数プロキシ  (Claude Code用)")
    global env_status_label, env_listbox
    current_env = get_env_proxy_status()
    env_status_label = make_status(env_sec, f"現在: {current_env}" if current_env else "現在: 無効")
    env_listbox = make_listbox(env_sec)
    make_btn_row(env_sec, "環境変数 ON", set_env_proxy,
                 "環境変数 OFF", disable_env_proxy)

    # ── IPリスト管理 ──────────────────────────────
    mgmt_sec = make_section(main_frame, "IPリスト管理")
    global mgmt_listbox, entry_var
    entry_var = tk.StringVar()

    entry_row = tk.Frame(mgmt_sec)
    entry_row.pack(fill=tk.X, pady=(0, 4))
    tk.Label(entry_row, text="追加:").pack(side=tk.LEFT)
    tk.Entry(entry_row, textvariable=entry_var, width=28).pack(side=tk.LEFT, padx=6)
    tk.Label(entry_row, text="例: 172.20.1.1:8080", fg="#888888").pack(side=tk.LEFT)

    mgmt_listbox = make_listbox(mgmt_sec, height=4)

    add_row = tk.Frame(mgmt_sec)
    add_row.pack(pady=(0, 4))
    tk.Button(add_row, text="追加", command=add_proxy, width=BTN_W,
              bg="#c3e6cb", activebackground="#a3d9a5").pack(side=tk.LEFT, padx=6)
    tk.Button(add_row, text="削除", command=remove_proxy, width=BTN_W,
              bg="#f5c6cb", activebackground="#e09ba1").pack(side=tk.LEFT, padx=6)

    # ── BAT ファイル ──────────────────────────────
    bat_sec = make_section(main_frame, "BAT ファイル")
    global bat_label
    config = load_ini()
    bat_path = config["Settings"].get("batPath", "")
    bat_label = tk.Label(bat_sec,
                         text=f"設定: {bat_path}" if bat_path else "batファイルが設定されていません",
                         wraplength=400, anchor="w", fg="#555555", justify="left")
    bat_label.pack(fill=tk.X, pady=(0, 4))
    make_btn_row(bat_sec, "ファイルを選択", select_bat_file,
                 "ファイルを実行", run_bat_file)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
