"""MarkiNote - Markdown 文档管理系统启动文件"""
import json
import os
import socket
import sys
import threading
import webbrowser

# Windows 控制台默认 GBK 编码，输出 emoji 会直接抛 UnicodeEncodeError 崩溃
# （stdout 被重定向时尤其明显，例如打包成 exe 双击运行、或输出到日志文件）。
# 打包成窗口程序时 sys.stdout 可能为 None 或不可重配置的对象，一律忽略。
if sys.platform == 'win32':
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

from app import create_app

# 创建Flask应用实例
app = create_app()

APP_NAME = 'MarkiNote'
DEFAULT_PORT = 5000


def find_free_port(host, preferred=DEFAULT_PORT):
    """优先使用 preferred 端口；被占用时让系统分配一个空闲端口

    端口写死会让第二次启动静默失败，对"点击即用"的软件是致命的。
    """
    for candidate in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, candidate))
                return sock.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError(f'在 {host} 上找不到可用端口')


def running_instance_on(host, port):
    """判断该端口上是否已经跑着一个 MarkiNote 实例

    只认健康检查返回的标识，不能只看端口是否被占用——那个端口上
    可能是别的程序。
    """
    import urllib.request
    try:
        url = f'http://{host}:{port}/api/health'
        with urllib.request.urlopen(url, timeout=1.5) as resp:
            return json.loads(resp.read().decode('utf-8')).get('app') == APP_NAME
    except Exception:
        return False


def open_native_window(url):
    """用原生窗口打开界面。返回 False 表示不可用，应改用系统浏览器

    依赖 pywebview + WebView2（Windows 11 自带）。任何异常都回退，
    不让"窗口起不来"演变成"软件打不开"。
    """
    try:
        import webview
    except ImportError:
        return False
    try:
        webview.create_window(APP_NAME, url)
        webview.start()
        return True
    except Exception as exc:
        print(f"⚠️  原生窗口不可用（{exc}），改用系统浏览器")
        return False


def serve(host, port, debug):
    """在当前线程启动 Flask 服务"""
    app.run(debug=debug, host=host, port=port, use_reloader=False, threaded=True)


if __name__ == '__main__':
    # 默认只监听本机，调试模式默认关闭
    host = os.environ.get('MARKINOTE_HOST', '127.0.0.1')
    debug = os.environ.get('MARKINOTE_DEBUG') == '1'
    requested = int(os.environ.get('MARKINOTE_PORT') or DEFAULT_PORT)
    want_window = os.environ.get('MARKINOTE_WINDOW', '1') != '0' and not debug
    open_browser = os.environ.get('MARKINOTE_NO_BROWSER') != '1'

    # 单实例：目标端口上已经有 MarkiNote 在跑，就打开它，而不是再起一个服务
    if not debug and running_instance_on(host, requested):
        url = f'http://{host}:{requested}'
        print(f"MarkiNote 已在运行，正在打开 {url}")
        if open_browser:
            webbrowser.open(url)
        sys.exit(0)

    port = find_free_port(host, requested)
    url = f'http://{host}:{port}'

    print("🚀 MarkiNote 启动中...")
    print(f"📝 访问 {url} 使用应用")
    print(f"📁 文档目录: {app.config['LIBRARY_FOLDER']}")
    print("🐱 By wink-wink-wink555")
    if port != requested:
        print(f"⚠️  端口 {requested} 被占用，已改用 {port}")

    if want_window:
        # 原生窗口要占用主线程，服务放到后台线程
        threading.Thread(target=serve, args=(host, port, debug), daemon=True).start()
        if open_native_window(url):
            # 用户关掉了窗口，进程就该结束——否则会留下一个占着端口的僵尸进程
            sys.exit(0)
        # 原生窗口不可用，退回浏览器；主线程没有别的事做，保持进程存活
        if open_browser:
            webbrowser.open(url)
        threading.Event().wait()
    else:
        # 纯服务模式：主线程跑 Flask，浏览器由定时器打开
        if open_browser and not debug:
            threading.Timer(1.5, lambda: webbrowser.open(url)).start()
        serve(host, port, debug)
