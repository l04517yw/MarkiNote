"""MarkiNote - Markdown 文档管理系统启动文件"""
import os
import socket
import sys

# Windows 控制台默认 GBK 编码，输出 emoji 会直接抛 UnicodeEncodeError 崩溃
# （stdout 被重定向时尤其明显，例如打包成 exe 双击运行、或输出到日志文件）
if sys.platform == 'win32':
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass

from app import create_app

# 创建Flask应用实例
app = create_app()


def find_free_port(host, preferred=5000):
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


if __name__ == '__main__':
    # 默认只监听本机，调试模式默认关闭
    host = os.environ.get('MARKINOTE_HOST', '127.0.0.1')
    debug = os.environ.get('MARKINOTE_DEBUG') == '1'
    port = int(os.environ.get('MARKINOTE_PORT') or find_free_port(host))

    print("🚀 MarkiNote 启动中...")
    print(f"📝 访问 http://{host}:{port} 使用应用")
    print(f"📁 文档目录: {app.config['LIBRARY_FOLDER']}")
    print("🐱 By wink-wink-wink555")
    app.run(debug=debug, host=host, port=port, use_reloader=debug)
