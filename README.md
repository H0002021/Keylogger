### 键盘记录器
# 你在克隆此仓库后可以执行 "一键启动.bat" 可直接运行
```python

# 1. 建立并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 2. 安装依赖
pip install pynput

# 3.启动程序
python app.py

# 前台运行（实时打印日志）
python app.py
# -q 是 “quiet”安静运行（不在终端输出，但显示终端）
python app.py -q
# -d 是 “daemon”静默后台运行（不在终端输出，关闭终端后仍然工作）
python app.py -d
# 运行后按ctrl+shift+f12停止次程序
2026-02-28 13:36:10 - Key pressed: ctrl+shift+f12
2026-02-28 13:36:10 - 程序已停止 (Ctrl+Shift+F12)
```

### 运行效果

```
2026-02-28 13:36:00 - Key pressed: <alt_gr>
2026-02-28 13:36:05 - Key pressed: m
2026-02-28 13:36:06 - Key pressed: shift+?
2026-02-28 13:36:07 - Mouse: 左键按下
2026-02-28 13:36:07 - Mouse: 左键松开
2026-02-28 13:36:08 - Mouse: 左键按下
2026-02-28 13:36:08 - Mouse: 左键松开
2026-02-28 13:36:10 - Key pressed: ctrl+shift+f12
2026-02-28 13:36:10 - 程序已停止 (Ctrl+Shift+F12)
```

### 目录结构

```python
Keylogger
  ├─ images
  ├─ python-3.12.10-embed-amd64
  ├─ app copy.py       #没有"-q" "-d"参数
  ├─ app.py
  ├─ input_log.txt     #输入日志文件
  ├─ input_log2.txt    #输入日志文件的备份文件
  ├─ README.md
  └─ 一键启动.bat
```

### 代码结构概览

```
app.py
 ├─ class InputLogger
 │   ├─ __init__(quiet=False)        # 初始化、读取配置
 │   ├─ write_log(message)           # 带时间戳的写入（quiet 时不 print）
 │   ├─ normalize_key(key)           # 统一键名 + 小键盘映射
 │   ├─ check_exit_hotkey()          # 检测 Ctrl+Shift+Alt+F12
 │   ├─ on_key_press(key)            # 过滤重复、生成组合键日志
 │   ├─ on_key_release(key)          # 记录松开事件
 │   ├─ on_click(x, y, button, p)    # 记录鼠标点击
 │   ├─ rotate_log()                 # 启动时自动备份旧日志
 │   └─ start_logging()              # 启动监听器、阻塞主线程
 ├─ daemonize_unix()                 # Unix 双 fork（后台模式）
 ├─ launch_windows_daemon()           # Windows 使用 pythonw 重启
 └─ 主入口
      ├─ argparse 解析 -q / -d
      ├─ signal.signal(SIGINT, ignore_sigint)
      └─ logger = InputLogger(quiet=args.quiet)
          logger.start_logging()
```

### 已知BUG

1，运行后鼠标**选择终端文本时**，电脑会卡住。在终端内敲一下回车即可恢复

![PixPin_2026-03-01_14-32-25](images\PixPin_2026-03-01_14-32-25.png)

2，
