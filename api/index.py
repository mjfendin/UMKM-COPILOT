"""Vercel serverless entry point for UMKM Copilot"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# For Vercel serverless
application = app

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
