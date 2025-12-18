# HaulConnect

A modern logistics platform connecting drivers, dispatchers, and brokers. Built with Flask.

## Features

- **Load Board**: Browse and post available loads
- **Dispatch Management**: Streamlined dispatch operations
- **Messaging**: Real-time communication between users
- **User Authentication**: Secure login/registration with role-based access

## Project Structure

```
HaulConnect/
├── app.py                  # Application entry point
├── config.py               # Configuration settings
├── extensions.py           # Flask extensions
├── requirements.txt        # Python dependencies
├── app/
│   ├── __init__.py         # Application factory
│   ├── models/             # Database models
│   ├── auth/               # Authentication blueprint
│   ├── messaging/          # Messaging blueprint
│   ├── dispatch/           # Dispatch blueprint
│   ├── main/               # Main routes blueprint
│   ├── templates/          # Jinja2 templates
│   └── static/             # Static assets
├── migrations/             # Database migrations
└── tests/                  # Test suite
```

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

1. **Clone the repository**
   ```bash
   cd Cursor_HaulConnect
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open in browser**
   Navigate to `http://localhost:5000`

## Configuration

Environment variables (set in `.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment mode | `development` |
| `SECRET_KEY` | Secret key for sessions | (generated) |
| `DATABASE_URL` | Database connection string | SQLite |

## Development

### Running Tests
```bash
pytest tests/
```

### Database Migrations
```bash
# Initialize migrations (first time only)
flask db init

# Create a new migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade
```

## Tech Stack

- **Backend**: Flask 3.0
- **Database**: SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF
- **Migrations**: Flask-Migrate

## License

MIT License
