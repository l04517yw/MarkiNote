"""文件处理相关工具函数"""
import re
import os

def allowed_file(filename, allowed_extensions):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def resolve_library_path(base_path, user_path):
    """把用户传入的相对路径安全地解析到文档库目录内

    Args:
        base_path: 文档库根目录
        user_path: 用户传入的相对路径（可为空字符串，表示根目录）

    Returns:
        解析后的绝对路径；若路径试图逃逸出文档库目录则返回 None

    原实现用 os.path.abspath(full).startswith(os.path.abspath(base)) 做校验，
    这个判断有两个缺陷：
      1. 'lib_backup/x.md' 的绝对路径确实以 'lib' 开头，会被误判为合法，
         而它其实指向文档库的兄弟目录；
      2. os.path.join(base, '/etc/passwd') 会直接丢掉 base，返回绝对路径。
    这里改用"先拒绝绝对路径，再校验是否真正位于 base 之下"的方式。
    """
    if not user_path:
        return os.path.realpath(base_path)

    # 拒绝绝对路径和 Windows 盘符相对路径（如 'C:foo'）
    if os.path.isabs(user_path) or os.path.splitdrive(user_path)[0]:
        return None

    base = os.path.realpath(base_path)
    full = os.path.realpath(os.path.join(base_path, user_path))

    if full == base:
        return full
    # 必须位于 base 之下，且分隔符要跟着 base，避免 'lib2' 被误认为在 'lib' 内
    if not full.startswith(base + os.sep):
        return None
    return full

def safe_filename(filename):
    """
    安全的文件名处理，支持中文字符
    只移除路径分隔符和其他危险字符，保留中文
    """
    # 移除路径分隔符和其他危险字符
    # 保留中文、英文、数字、点、下划线、连字符、空格、括号
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    
    # 移除开头和结尾的空格和点
    filename = filename.strip('. ')
    
    # 如果文件名为空或只有扩展名，使用默认名称
    if not filename or filename.startswith('.'):
        filename = 'unnamed' + filename
    
    # 限制文件名长度（保留扩展名）
    name, ext = os.path.splitext(filename)
    if len(name.encode('utf-8')) > 200:
        # 截断时保证不会截断中文字符的一半
        name = name[:100]
    
    return name + ext

