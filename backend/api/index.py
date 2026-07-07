"""Vercel serverless entry point."""
import sys
import os

# Get the backend directory (parent of api/)
current_dir = os.path.dirname(os.path.abspath(__file__))  # .../backend/api
backend_dir = os.path.dirname(current_dir)                 # .../backend

sys.path.insert(0, backend_dir)
sys.path.insert(0, current_dir)

os.chdir(backend_dir)

from app import app

handler = app
