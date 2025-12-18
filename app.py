"""
HaulConnect Application Entry Point

Run this file to start the Flask development server:
    python app.py

For production, use a WSGI server like Gunicorn:
    gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
"""

from app import create_app

# Create application instance
app = create_app()

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True
    )

