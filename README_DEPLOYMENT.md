# HaulConnect Deployment Guide

## Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Cursor_HaulConnect
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
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

5. **Initialize database**
   ```bash
   python app.py
   # Database will be created automatically in instance/haulconnect.db
   ```

6. **Run the application**
   ```bash
   python app.py
   # Or use Flask CLI:
   flask run
   ```

### Production Deployment

#### Heroku

1. **Install Heroku CLI** and login
   ```bash
   heroku login
   ```

2. **Create Heroku app**
   ```bash
   heroku create haulconnect-app
   ```

3. **Set environment variables**
   ```bash
   heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   heroku config:set FLASK_ENV=production
   heroku config:set AUTH_PASSWORD_REQUIRED=true
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

#### Render

1. **Create new Web Service** on Render
2. **Connect your repository**
3. **Set build command**: `pip install -r requirements.txt`
4. **Set start command**: `gunicorn --bind=0.0.0.0:$PORT "app:create_app()"`
5. **Add environment variables**:
   - `SECRET_KEY`: Generate a strong random key
   - `FLASK_ENV`: `production`
   - `AUTH_PASSWORD_REQUIRED`: `true`
   - `DATABASE_URL`: Render will provide PostgreSQL URL automatically

#### Docker (Optional)

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]
   ```

2. **Build and run**
   ```bash
   docker build -t haulconnect .
   docker run -p 5000:5000 -e SECRET_KEY=your-key haulconnect
   ```

## Environment Variables

### Required (Production)

- `SECRET_KEY`: Strong random secret key for session encryption
- `FLASK_ENV`: Set to `production` for production deployments
- `AUTH_PASSWORD_REQUIRED`: Must be `true` in production

### Optional

- `DATABASE_URL`: Database connection string (defaults to SQLite in instance/)
- `HUBSPOT_ACCESS_TOKEN`: HubSpot integration token (if using)
- `FLASK_DEBUG`: Set to `False` in production

## Security Checklist

- [ ] `SECRET_KEY` is set to a strong random value
- [ ] `FLASK_DEBUG=False` in production
- [ ] `AUTH_PASSWORD_REQUIRED=true` in production
- [ ] `.env` file is in `.gitignore` (never commit secrets)
- [ ] Database credentials are secure
- [ ] HTTPS is enabled (via reverse proxy or platform)
- [ ] Simulation tools are disabled (only available when `DEBUG=True`)

## Testing

Run the test suite:

```bash
pip install pytest
pytest tests/ -v
```

## Database Migrations

If using Flask-Migrate:

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## Troubleshooting

### Database Issues

- Ensure `instance/` directory exists and is writable
- Check database URL in `.env`
- For SQLite: ensure path uses `instance/` directory

### Import Errors

- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`
- Check Python version (3.11+ recommended)

### Port Issues

- Default port is 5000
- Use `PORT` environment variable for cloud platforms
- Gunicorn will bind to `0.0.0.0:$PORT` automatically

## Support

For issues or questions, please refer to the main README.md or open an issue in the repository.

