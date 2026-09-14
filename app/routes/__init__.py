"""路由模块"""
from .main_routes import main_bp
from .library_routes import library_bp
from .asset_routes import asset_bp
from .search_routes import search_bp
from .trash_routes import trash_bp

__all__ = [
    'main_bp',
    'library_bp',
    'asset_bp',
    'search_bp',
    'trash_bp',
]
