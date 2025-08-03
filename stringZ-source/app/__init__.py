from flask import Flask
from flask_session import Session
from config import DevelopmentConfig
import tempfile

def create_app(config_class=DevelopmentConfig):
    """Flask Application factory"""
    app = Flask(__name__,
                template_folder="../templates",
                static_folder="static")
    app.config.from_object(config_class)


    # Session configs
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = tempfile.gettempdir()
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = False

    Session(app)

    # Blueprints register
    from app.routes.main import main_bp
    from app.routes.upload import upload_bp
    from app.routes.download import download_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(api_bp)

    return app
