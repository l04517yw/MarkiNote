"""全文检索

原来的搜索是纯前端行为：只过滤**当前目录已经渲染出来的文件名**。
不搜正文、不搜子目录，而且切换目录后过滤会失效（搜索框里还有字，
列表却已经不按它过滤了）。

这里在服务端递归扫描文档库，返回「文件 + 行号 + 上下文片段」。
文档库通常是几百个文件的量级，直接扫足够快，不需要引入索引引擎。
"""
import os

from flask import Blueprint, current_app, jsonify, request

from app.utils import resolve_library_path

search_bp = Blueprint('search', __name__)

MAX_MATCHES = 200        # 总命中上限，避免超大结果集把前端拖死
MAX_FILES = 60           # 最多返回多少个文件
MAX_FILE_BYTES = 2 * 1024 * 1024   # 跳过超大文件
SNIPPET_PAD = 40         # 片段在关键词两侧各留多少字符


def _document_extensions():
    return ('md', 'markdown', 'txt')


def _iter_documents(library_dir):
    """递归产出 (绝对路径, 库内相对路径, 文件名)"""
    for root, dirs, files in os.walk(library_dir):
        # 跳过隐藏目录（回收站不在这里，但外部编辑器可能留下 .git 之类）
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        for name in sorted(files):
            if name.startswith('.'):
                continue
            ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
            if ext not in _document_extensions():
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, library_dir).replace('\\', '/')
            yield full, rel, name


@search_bp.route('/api/search', methods=['GET'])
def search():
    """在文档库内检索正文

    返回按文件分组的命中，每组带行号与上下文片段。
    """
    query = (request.args.get('q') or '').strip()
    if not query:
        return jsonify({'success': True, 'query': '', 'files': [], 'total': 0, 'truncated': False})

    # scope 可选，用于把检索限定在某个子目录内，同样要过路径校验
    scope = request.args.get('scope', '')
    if scope:
        library_dir = resolve_library_path(current_app.config['LIBRARY_FOLDER'], scope)
        if library_dir is None or not os.path.isdir(library_dir):
            return jsonify({'error': '非法路径'}), 403
    else:
        library_dir = current_app.config['LIBRARY_FOLDER']

    needle = query.lower()
    files = []
    total = 0
    truncated = False

    for full, rel, name in _iter_documents(library_dir):
        if truncated:
            break
        try:
            if os.path.getsize(full) > MAX_FILE_BYTES:
                continue
            with open(full, encoding='utf-8', errors='replace') as handle:
                lines = handle.read().splitlines()
        except OSError:
            continue

        hits = []
        for index, line in enumerate(lines, 1):
            lowered = line.lower()
            at = lowered.find(needle)
            if at < 0:
                continue

            # 去掉 Markdown 行首标记，让片段更像正文而不是源码
            snippet = line.strip()
            stripped_at = max(0, at - SNIPPET_PAD)
            snippet_text = snippet[stripped_at:stripped_at + 140]
            if stripped_at > 0:
                snippet_text = '…' + snippet_text
            if stripped_at + 140 < len(snippet):
                snippet_text += '…'

            hits.append({'line': index, 'text': snippet_text})
            total += 1
            if total >= MAX_MATCHES:
                truncated = True
                break

        if hits:
            files.append({'path': rel, 'name': name, 'count': len(hits), 'hits': hits})
            if len(files) >= MAX_FILES:
                truncated = True

    return jsonify({
        'success': True,
        'query': query,
        'files': files,
        'total': total,
        'truncated': truncated,
    })
