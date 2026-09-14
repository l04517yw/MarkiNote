"""回收站路由

删除走 move_to_trash，这里提供查看、还原、彻底删除、清空。
条目 id 由服务端生成、客户端回传，因此每个入口都要先校验格式
（见 trash.is_valid_entry_id），否则它会被拼进路径。
"""
from flask import Blueprint, current_app, jsonify, request

from app.utils.trash import empty, is_valid_entry_id, list_trash, purge, restore

trash_bp = Blueprint('trash', __name__)


def _require_entry_id():
    """从请求体里取条目 id 并校验，非法时返回 (None, 错误响应)"""
    data = request.get_json(silent=True) or {}
    entry_id = data.get('id', '')
    if not is_valid_entry_id(entry_id):
        return None, (jsonify({'error': '条目 id 无效'}), 400)
    return entry_id, None


@trash_bp.route('/api/trash/list', methods=['GET'])
def list_items():
    """回收站内容，最近的在前"""
    data_dir = current_app.config['DATA_DIR']
    return jsonify({'success': True, 'items': list_trash(data_dir)})


@trash_bp.route('/api/trash/restore', methods=['POST'])
def restore_item():
    """还原一条回它原来的位置"""
    entry_id, error = _require_entry_id()
    if error:
        return error

    data_dir = current_app.config['DATA_DIR']
    library_dir = current_app.config['LIBRARY_FOLDER']
    ok, message = restore(data_dir, library_dir, entry_id)
    if not ok:
        return jsonify({'error': message}), 400
    return jsonify({'success': True, 'message': message})


@trash_bp.route('/api/trash/purge', methods=['POST'])
def purge_item():
    """彻底删除一条，不可恢复"""
    entry_id, error = _require_entry_id()
    if error:
        return error

    data_dir = current_app.config['DATA_DIR']
    ok, message = purge(data_dir, entry_id)
    if not ok:
        return jsonify({'error': message}), 500
    return jsonify({'success': True, 'message': message})


@trash_bp.route('/api/trash/empty', methods=['POST'])
def empty_trash():
    """清空回收站"""
    data_dir = current_app.config['DATA_DIR']
    removed, failed = empty(data_dir)

    message = f'已彻底删除 {removed} 项'
    if failed:
        message += f'，{len(failed)} 项未能删除'

    return jsonify({
        'success': True,
        'removed': removed,
        'failed': len(failed),
        'message': message,
    })
