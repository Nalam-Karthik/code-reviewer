# flask-api/run.py

from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True → auto-reload when you save a file (dev only)
    # host="0.0.0.0" → listen on all interfaces inside Docker
    app.run(host="0.0.0.0", port=5000, debug=True)