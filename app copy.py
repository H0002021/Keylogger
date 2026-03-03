#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import signal
from datetime import datetime
from pynput import keyboard, mouse


# --------------------------------------------------------------
#   输入记录器
# --------------------------------------------------------------
class InputLogger:
    """键盘/鼠标记录器（组合键、防重复、热键退出、日志轮转、数字小键盘友好）"""

    # 退出热键（统一成 <…> 形式）
    EXIT_HOTKEY = {"<ctrl>", "<shift>", "<alt>", "<f12>"}

    # 控制字符（Ctrl+A~Z）映射为普通字符
    _CTRL_CHAR_MAP = {i: chr(i + 96) for i in range(1, 27)}  # 1->a … 26->z
    _CTRL_CHAR_MAP.update({
        0:   "space",
        9:   "tab",
        10:  "enter",
        13:  "enter",
        27:  "esc",
        8:   "backspace",
        127: "del"
    })

    # ---------- 小键盘映射 ----------
    # vk → 可读文字（仅列出常用键，其它键交给后面的统一处理）
    _NUMPAD_MAP = {
        96:  "数字键盘 0",
        97:  "数字键盘 1",
        98:  "数字键盘 2",
        99:  "数字键盘 3",
        100: "数字键盘 4",
        101: "数字键盘 5",
        102: "数字键盘 6",
        103: "数字键盘 7",
        104: "数字键盘 8",
        105: "数字键盘 9",
        106: "数字键盘 *",
        107: "数字键盘 +",
        108: "数字键盘 Enter",
        109: "数字键盘 -",
        110: "数字键盘 .",
        111: "数字键盘 /",
    }

    # --------------------------------------------------------------
    def __init__(self):
        self.log_file = "input_log.txt"
        self.pressed_keys = set()
        self.kb_listener = None
        self.ms_listener = None

    # ---------- 写日志 ----------
    def write_log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} - {message}"
        print(line)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    # ---------- 统一键名 ----------
    def normalize_key(self, key) -> str:
        """
        把 pynput 的 key 对象统一为四类字符串：

        1) 普通可打印字符           →  'a', '1', ';' …
        2) 控制字符（Ctrl+A~Z）     →  对应的普通字母或 space/enter …
        3) 修饰键                  →  '<ctrl>', '<alt>', '<shift>', '<cmd>'
        4) 其它功能键（包括数字小键盘）→  '<f1>', '<left>', '数字键盘 0' …
        """
        # -------------------------------------------------
        # ① 先处理 **数字小键盘**（vk 96‑111）
        # -------------------------------------------------
        if isinstance(key, keyboard.KeyCode):
            vk = getattr(key, "vk", None)
            if vk is not None:
                # 若在小键盘映射表里，直接返回对应文字
                if vk in self._NUMPAD_MAP:
                    return self._NUMPAD_MAP[vk]

        # -------------------------------------------------
        # ② 处理普通字符（ASCII >= 32）
        # -------------------------------------------------
        try:
            ch = key.char
            if ch is not None:
                if ord(ch) >= 32:                # 正常可打印字符
                    return ch
                # 控制字符（Ctrl+A …），使用映射表转成普通字母/space 等
                mapped = self._CTRL_CHAR_MAP.get(ord(ch))
                if mapped is not None:
                    return mapped
                return f"ctrl+{ord(ch)}"
        except AttributeError:
            pass

        # -------------------------------------------------
        # ③ 非字符键（功能键、修饰键）统一为 <…> 形式
        # -------------------------------------------------
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
        """四键全部在 pressed_keys 中时安全退出"""
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

        # 防止系统层面的键重复（长按会产生多次 press）
        if key_name in self.pressed_keys:
            return

        # 放入集合，供后续 release 与组合键使用
        self.pressed_keys.add(key_name)

        # 立即检查是否触发退出热键
        self.check_exit_hotkey()

        # 组合键的记录逻辑
        modifiers = [m for m in ("<ctrl>", "<alt>", "<shift>", "<cmd>")
                     if m in self.pressed_keys]

        # 当前键本身是修饰键时，只记录一次 “Key 按下: <ctrl>”
        if key_name in ("<ctrl>", "<alt>", "<shift>", "<cmd>"):
            self.write_log(f"Key 按下: {key_name}")
            return

        # 有修饰键 → 拼出组合键；没有则只记录普通键按下
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
        btn_name = str(button).replace("Button.", "").lower()
        act = "按下" if pressed else "松开"
        self.write_log(f"Mouse: {btn_name} {act}")

    # ---------- 日志文件搬迁 ----------
    def rotate_log(self):
        """
        启动时执行一次：
        * 若只有 input_log.txt → 改名为 input_log2.txt
        * 若两者都存在 → 删除旧的 input_log2.txt 再改名
        * 若不存在 input_log.txt → 什么也不做
        """
        old = "input_log.txt"
        backup = "input_log2.txt"

        if os.path.exists(old):
            if os.path.exists(backup):
                try:
                    os.remove(backup)
                except OSError as e:
                    self.write_log(f"删除旧备份 {backup} 失败: {e}")

            try:
                os.rename(old, backup)
                self.write_log(f"已把 {old} 重命名为 {backup}")
            except OSError as e:
                self.write_log(f"重命名日志文件失败: {e}")

    # ---------- 程序启动 ----------
    def start_logging(self):
        # ★ 先把旧日志搬走，确保本次运行使用全新的 input_log.txt ★
        self.rotate_log()
        self.write_log("程序启动")

        # 创建监听器并保存，以便后面主动 stop()
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
#   入口 & SIGINT（Ctrl+C）拦截
# --------------------------------------------------------------
def ignore_sigint(signum, frame):
    """
    把终端里的 Ctrl+C（SIGINT）拦截，使其不直接终止进程。
    若想让 Ctrl+C 立刻退出，只把下面的 `pass` 改成 `sys.exit(0)`.
    """
    print("\n收到 SIGINT（Ctrl+C），已拦截，继续运行…")
    # pass          # 直接忽略
    # sys.exit(0)   # 若想直接退出，取消注释此行


if __name__ == "__main__":
    # 把 SIGINT 绑定到自定义处理函数
    signal.signal(signal.SIGINT, ignore_sigint)

    logger = InputLogger()
    logger.start_logging()
