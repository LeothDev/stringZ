import tempfile
import os

class Config:
    # FLask settings

    # File upload settings
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024 # 500MB
    # UPLOAD_FOLDER = tempfile.gettempdir()
    # UPLOAD_FOLDER = './uploads'

    # Docker!
    if os.environ.get('DOCKER_CONTAINER'):
        UPLOAD_FOLDER = '/app/uploads'
    else:
        UPLOAD_FOLDER = tempfile.gettempdir()

    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Usually I set a secret key, but since it only runs locally, there's no need
