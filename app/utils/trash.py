"""回收站

删除不再是物理删除：先把文件/文件夹移进数据目录下的 trash/，同时写一份
同名的 .json 元信息记录它原来的位置。还原时读元信息搬回去。

放在文档库**外面**（`<数据目录>/trash`）而不是库内的 `.trash`：库内的话，
移动文件时的文件夹选择列表（走 os.listdir，不跳过隐藏项）会把它露出来。
"""
import json
import os
import re
import shutil
from datetime import datetime

TRASH_DIRNAME = 'trash'

# 条目 id 由服务端生成，形如 20260914-131500-a1b2c3。
# 客户端会把 id 回传过来用于还原/彻底删除，而它会被拼进路径，
# 所以必须严格校验格式，不能让 '../..' 之类的值透进去。
ENTRY_ID_PATTERN = re.compile(r'^\d{8}-\d{6}-[0-9a-f]{6}$')


def is_valid_entry_id(entry_id):
    """校验条目 id 是否是本模块生成的那种"""
    return isinstance(entry_id, str) and bool(ENTRY_ID_PATTERN.match(entry_id))


def get_trash_dir(data_dir):
    """回收站目录（可能还不存在）"""
    return os.path.join(data_dir, TRASH_DIRNAME)


def _new_entry_id():
    """时间戳 + 随机后缀，保证同一秒内多条也不冲突，且天然按时间排序"""
    return datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + os.urandom(3).hex()


def _path_size(path):
    """文件或文件夹占用的字节数；算不出来就返回 0，不因为这个失败而中断删除"""
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
        total = 0
        for root, _dirs, files in os.walk(path):
            for name in files:
                try:
                    total += os.path.getsize(os.path.join(root, name))
                except OSError:
                    continue
        return total
    except OSError:
        return 0


def _meta_path(trash_dir, entry_id):
    return os.path.join(trash_dir, entry_id + '.json')


def _read_meta(trash_dir, entry_id):
    if not is_valid_entry_id(entry_id):
        return None
    try:
        with open(_meta_path(trash_dir, entry_id), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def move_to_trash(data_dir, full_path, original_path):
    """把文件或文件夹移进回收站

    Args:
        data_dir: 用户数据目录
        full_path: 要删除的绝对路径
        original_path: 它在文档库中的相对路径（还原时用）

    Returns:
        回收站条目 id
    """
    trash_dir = get_trash_dir(data_dir)
    os.makedirs(trash_dir, exist_ok=True)

    entry_id = _new_entry_id()
    is_dir = os.path.isdir(full_path)
    normalised = original_path.replace('\\', '/')

    # 先落元信息再搬文件：万一搬运失败，索引至少是完整的，
    # 不会出现"文件在回收站里但不知道它原来在哪"的孤儿条目
    meta = {
        'id': entry_id,
        'name': os.path.basename(normalised.rstrip('/')) or normalised,
        'original_path': normalised,
        'type': 'folder' if is_dir else 'file',
        'size': _path_size(full_path),
        'deleted_at': datetime.now().isoformat(timespec='seconds'),
    }
    with open(_meta_path(trash_dir, entry_id), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    shutil.move(full_path, os.path.join(trash_dir, entry_id))
    return entry_id


def list_trash(data_dir):
    """回收站条目，最近的在前"""
    trash_dir = get_trash_dir(data_dir)
    if not os.path.isdir(trash_dir):
        return []

    entries = []
    for name in os.listdir(trash_dir):
        if not name.endswith('.json'):
            continue
        meta = _read_meta(trash_dir, name[:-5])
        if not meta or 'id' not in meta:
            continue
        meta['exists'] = os.path.exists(os.path.join(trash_dir, meta['id']))
        entries.append(meta)

    entries.sort(key=lambda item: item.get('deleted_at', ''), reverse=True)
    return entries


def restore(data_dir, library_dir, entry_id):
    """把条目还原回它原来的位置

    Returns:
        (成功?, 提示信息)
    """
    trash_dir = get_trash_dir(data_dir)
    meta = _read_meta(trash_dir, entry_id)
    if not meta:
        return False, '回收站里找不到这条记录'

    payload = os.path.join(trash_dir, entry_id)
    if not os.path.exists(payload):
        return False, '文件已不在回收站中'

    target = os.path.join(library_dir, meta['original_path'])
    if os.path.exists(target):
        return False, f'原位置已有同名{"文件夹" if meta["type"] == "folder" else "文件"}，请先处理'

    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.move(payload, target)
    except OSError as exc:
        return False, f'还原失败：{exc}'

    try:
        os.remove(_meta_path(trash_dir, entry_id))
    except OSError:
        pass
    return True, f'已还原到 {meta["original_path"]}'


def purge(data_dir, entry_id):
    """彻底删除一条"""
    trash_dir = get_trash_dir(data_dir)
    payload = os.path.join(trash_dir, entry_id)
    try:
        if os.path.isdir(payload):
            shutil.rmtree(payload)
        elif os.path.isfile(payload):
            os.remove(payload)
        os.remove(_meta_path(trash_dir, entry_id))
    except OSError as exc:
        return False, f'删除失败：{exc}'
    return True, '已彻底删除'


def empty(data_dir):
    """清空回收站

    Returns:
        (删掉的条目数, 失败的条目名)
    """
    trash_dir = get_trash_dir(data_dir)
    if not os.path.isdir(trash_dir):
        return 0, []

    removed = 0
    failed = []
    for name in os.listdir(trash_dir):
        if not name.endswith('.json'):
            continue
        entry_id = name[:-5]
        ok, _message = purge(data_dir, entry_id)
        if ok:
            removed += 1
        else:
            failed.append(entry_id)

    # 顺带清掉没有元信息、也搬不动的残留
    for name in os.listdir(trash_dir):
        full = os.path.join(trash_dir, name)
        try:
            if os.path.isdir(full):
                shutil.rmtree(full)
            else:
                os.remove(full)
        except OSError:
            failed.append(name)
    return removed, failed
