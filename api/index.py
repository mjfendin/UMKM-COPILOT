"""Vercel serverless entry — serves everything through Flask"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import send_from_directory
from app import app

# Serve static files through Flask (Vercel Python doesn't serve /static/)
@app.route('/static/<path:filename>')
def static_files(filename):
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
    return send_from_directory(static_dir, filename)

application = app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
