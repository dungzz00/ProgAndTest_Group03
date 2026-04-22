import os

DB_HOST     = os.environ.get('DB_HOST', 'localhost')
DB_PORT     = int(os.environ.get('DB_PORT', 3306))
DB_USER     = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'phandung1262006')
DB_NAME     = os.environ.get('DB_NAME', 'edums')

SECRET_KEY  = os.environ.get('SECRET_KEY', 'edums_jwt_secret_2024')
DEBUG       = True
PORT        = int(os.environ.get('PORT', 5000))