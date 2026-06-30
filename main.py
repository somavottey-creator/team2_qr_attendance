import os
from app import create_app

if __name__ == "__main__":
    app = create_app()
    
    # Looks for an environment variable named 'FLASK_ENV'. 
    # If it's not found, it defaults to True (development mode).
    is_debug = os.environ.get("FLASK_ENV") != "production"
    
    # Update it to look exactly like this:
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)