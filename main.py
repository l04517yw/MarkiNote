"""MarkiNote - Markdown 文档管理系统启动文件"""
import json
import os
import shutil
import socket
import sys
import threading
import urllib.parse
import webbrowser
from datetime import datetime

class _NullWriter:
    """兜底输出流

    打包成窗口程序后 stdout/stderr 可能不存在、不可写、或是个编码装不下
    非 ASCII 字符的流。而视图函数里的 print 一旦抛异常，整个请求就会变成
    HTTP 500 —— 所以输出流必须保证"永远写得进去"。
    """
    encoding = 'utf-8'
    errors = 'replace'

    def write(self, *_args):
        return 0

    def flush(self):
        pass

    def reconfigure(self, **_kwargs):
        pass

    def isatty(self):
        return False


def _make_stream_safe(stream):
    """返回一个保证可写、且能编码任意字符的输出流"""
    if stream is None:
        return _NullWriter()
    try:
        stream.reconfigure(encoding='utf-8', errors='replace')
        stream.flush()  # 探测底层句柄是否真的可用，而不只是对象存在
        return stream
    except Exception:
        return _NullWriter()


# 必须在任何 print 之前完成
sys.stdout = _make_stream_safe(sys.stdout)
sys.stderr = _make_stream_safe(sys.stderr)

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
        print(f"[警告] 原生窗口不可用（{exc}），改用系统浏览器")
        return False


def serve(host, port, debug):
    """在当前线程启动 Flask 服务"""
    app.run(debug=debug, host=host, port=port, use_reloader=False, threaded=True)


def document_from_argv(argv):
    """从命令行参数里找出一个要打开的文档路径

    安装包里注册了 .md/.markdown/.txt 的文件关联之后，双击这类文件会把
    路径作为参数传进来。这里只挑第一个看起来像文档的参数，忽略其他开关。
    """
    for arg in argv[1:]:
        if arg.startswith('-') or not os.path.isfile(arg):
            continue
        ext = os.path.splitext(arg)[1].lower().lstrip('.')
        if ext in ('md', 'markdown', 'txt'):
            return os.path.abspath(arg)
    return None


def prepare_startup_file(path, library_dir):
    """把要打开的文档整理成「库内相对路径」

    已经在库里就直接用；在库外的复制进库根目录（同名时加时间戳），
    这样双击一个刚下载的 .md 也能直接看，而不必先手动上传。
    """
    real_library = os.path.realpath(library_dir)
    real_path = os.path.realpath(path)

    if real_path.startswith(real_library + os.sep):
        return os.path.relpath(real_path, real_library).replace('\\', '/')

    name = os.path.basename(real_path)
    target = os.path.join(real_library, name)
    if os.path.exists(target):
        stem, ext = os.path.splitext(name)
        target = os.path.join(real_library, f'{stem}_{datetime.now():%Y%m%d_%H%M%S}{ext}')

    try:
        os.makedirs(real_library, exist_ok=True)
        shutil.copy2(real_path, target)
    except OSError as exc:
        print(f"[提示] 无法导入 {path}：{exc}")
        return None
    return os.path.basename(target)


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

    # 启动参数里带了文档（双击 .md，或命令行指定），让界面直接打开它
    startup_document = document_from_argv(sys.argv)
    if startup_document:
        opened = prepare_startup_file(startup_document, app.config['LIBRARY_FOLDER'])
        if opened:
            url += '?open=' + urllib.parse.quote(opened)
            print(f"[打开] {opened}")
        else:
            print(f"[提示] 无法打开 {startup_document}")

    print("MarkiNote 启动中...")
    print(f"[访问] {url}")
    print(f"[文档目录] {app.config['LIBRARY_FOLDER']}")
    print("By wink-wink-wink555")
    if port != requested:
        print(f"[警告] 端口 {requested} 被占用，已改用 {port}")

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
