"""Flask应用初始化"""
import os

from flask import Flask
from app.config import BASE_DIR, Config

def create_app():
    """创建并配置Flask应用

    Returns:
        Flask: 配置好的Flask应用实例
    """
    # 用绝对路径，避免打包后相对路径解析到临时目录而找不到资源
    app = Flask(__name__,
                template_folder=os.path.join(BASE_DIR, 'templates'),
                static_folder=os.path.join(BASE_DIR, 'static'))
    
    # 加载配置
    app.config.from_object(Config)
    
    # 初始化配置
    Config.init_app(app)
    
    # 注册蓝图
    from app.routes import main_bp, library_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(library_bp)
    
    return app

