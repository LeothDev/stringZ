import os
import tempfile

class Config:
    # FLask settings

    # File upload settings
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024 # 500MB
    UPLOAD_FOLDER = tempfile.gettempdir()

    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Usually I set a secret key, but since it only runs locally, there's no need
