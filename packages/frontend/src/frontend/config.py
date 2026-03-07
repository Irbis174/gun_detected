import os

BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8001')
ML_URL = os.getenv('ML_URL', 'http://localhost:8000')
PORT = os.getenv('PORT', 5000)