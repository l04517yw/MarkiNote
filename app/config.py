"""应用配置文件"""
import os
import shutil
import sys

APP_NAME = 'MarkiNote'

# 项目根目录（app/ 的上一级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir():
    """返回用户数据目录的绝对路径（跨平台，打包成 exe 后依然正确）

    不能再用相对于当前工作目录的 'lib'：打包后工作目录可能是临时解压目录
    或程序安装目录，用户笔记会写进去然后丢失，或者根本没有写入权限。
    """
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    elif sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    return os.path.join(base, APP_NAME)


def get_seed_dir():
    """内置示例文档目录（仓库里的 lib/），首次运行用它初始化数据目录"""
    return os.path.join(BASE_DIR, 'lib')


class Config:
    """Flask应用配置"""
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    LIBRARY_FOLDER = os.path.join(get_data_dir(), 'lib')
    ALLOWED_EXTENSIONS = {'md', 'markdown', 'txt'}

    @staticmethod
    def init_app(app):
        """初始化应用配置

        确保数据目录存在；首次运行（数据目录为空）时把内置示例文档复制进去，
        这样打包后用户第一次打开看到的是新手指南，而不是一个空目录。
        """
        library = app.config['LIBRARY_FOLDER']
        os.makedirs(library, exist_ok=True)

        # 已有内容说明不是首次运行，不要覆盖用户数据
        if any(not name.startswith('.') for name in os.listdir(library)):
            return

        seed = get_seed_dir()
        if not os.path.isdir(seed):
            return
        for name in os.listdir(seed):
            source = os.path.join(seed, name)
            if os.path.isfile(source):
                shutil.copy2(source, os.path.join(library, name))
