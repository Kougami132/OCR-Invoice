from flask import Flask

def create_app():
    app = Flask(__name__)

    # 注册路由
    from .routes import bp
    app.register_blueprint(bp, url_prefix='/ocr')

    return app
