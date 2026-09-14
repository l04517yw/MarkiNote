"""文档库内的图片/附件伺服

Markdown 里写 `![](图.png)` 时，浏览器以**页面地址**为基准解析这个相对路径，
落到 `/图.png` 上——那是 404。所以前端会把相对路径改写成
`/api/library/asset?path=...`，由这里做路径校验后把文件内容送出去。

只读，且只放行 ASSET_EXTENSIONS 里的类型；路径校验复用 resolve_library_path，
不另写一套。
"""
import mimetypes
import os

from flask import Blueprint, current_app, jsonify, request, send_file

from app.utils import resolve_library_path

asset_bp = Blueprint('asset', __name__)


@asset_bp.route('/api/library/asset', methods=['GET'])
def serve_asset():
    """按库内相对路径返回资源内容"""
    rel_path = request.args.get('path', '')
    if not rel_path:
        return jsonify({'error': '缺少路径'}), 400

    base_path = current_app.config['LIBRARY_FOLDER']
    full_path = resolve_library_path(base_path, rel_path)

    # 安全检查：路径必须真正位于文档库目录内
    if full_path is None:
        return jsonify({'error': '非法路径'}), 403

    if not os.path.isfile(full_path):
        return jsonify({'error': '资源不存在'}), 404

    ext = os.path.splitext(full_path)[1].lower().lstrip('.')
    if ext not in current_app.config['ASSET_EXTENSIONS']:
        return jsonify({'error': '不支持该类型的资源'}), 404

    mime, _encoding = mimetypes.guess_type(full_path)
    response = send_file(full_path, mimetype=mime or 'application/octet-stream')
    # 不按内容猜类型，避免伪装成图片的文件被当成别的类型处理
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # SVG 被当作顶层文档直接打开时，内嵌脚本会执行。sandbox 让这种直接访问
    # 变成不能执行脚本的静态文档；用 <img> 引用时本来就不会执行脚本。
    if ext == 'svg':
        response.headers['Content-Security-Policy'] = 'sandbox'

    return response
