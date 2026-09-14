"""自动备份

文档库是纯本地、无版本控制的，误操作一次内容就没了——回收站防手滑，
这个防灾难。启动时（每天最多一次）把库打包成带时间戳的 zip，只保留最近若干份。

备份文件放在 `<数据目录>/backups/`，和文档库平级，不会被列进文档列表。
"""
import os
import time
import zipfile
from datetime import datetime

BACKUP_DIRNAME = 'backups'
KEEP = 10                      # 最多保留多少份
MIN_INTERVAL_SECONDS = 20 * 3600   # 两次备份至少间隔多久（约一天）


def get_backup_dir(data_dir):
    return os.path.join(data_dir, BACKUP_DIRNAME)


def _existing_backups(backup_dir):
    if not os.path.isdir(backup_dir):
        return []
    paths = []
    for name in os.listdir(backup_dir):
        if name.startswith('markinote-') and name.endswith('.zip'):
            full = os.path.join(backup_dir, name)
            try:
                paths.append((os.path.getmtime(full), full))
            except OSError:
                continue
    return sorted(paths, reverse=True)


def _library_has_content(library_dir):
    """库为空就不备份，免得留一堆空包"""
    for root, dirs, files in os.walk(library_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for name in files:
            if not name.startswith('.'):
                return True
    return False


def prune(backup_dir, keep=KEEP):
    """只保留最近 keep 份，返回清掉的数量"""
    removed = 0
    for _mtime, path in _existing_backups(backup_dir)[keep:]:
        try:
            os.remove(path)
            removed += 1
        except OSError:
            continue
    return removed


def run_backup(data_dir, library_dir, force=False):
    """按需备份一次

    Args:
        data_dir: 用户数据目录
        library_dir: 文档库目录
        force: 忽略时间间隔，强制执行

    Returns:
        (是否执行了备份, 给用户看的说明)
    """
    if not os.path.isdir(library_dir) or not _library_has_content(library_dir):
        return False, '文档库为空，跳过备份'

    backup_dir = get_backup_dir(data_dir)
    existing = _existing_backups(backup_dir)

    if not force and existing:
        age = time.time() - existing[0][0]
        if age < MIN_INTERVAL_SECONDS:
            return False, '距上次备份不足一天，跳过'

    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    target = os.path.join(backup_dir, f'markinote-{stamp}.zip')

    try:
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as bundle:
            for root, dirs, files in os.walk(library_dir):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for name in files:
                    if name.startswith('.'):
                        continue
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, library_dir)
                    try:
                        bundle.write(full, rel)
                    except OSError:
                        continue
    except (OSError, zipfile.BadZipFile) as exc:
        # 备份失败不能影响启动
        try:
            os.remove(target)
        except OSError:
            pass
        return False, f'备份失败：{exc}'

    prune(backup_dir)
    size_kb = os.path.getsize(target) / 1024
    return True, f'已备份到 {os.path.basename(target)}（{size_kb:.0f} KB）'
