# Backend - HRMS Lite API

FastAPI backend for HRMS Lite application.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

3. API will be available at `http://localhost:8000`
4. API documentation at `http://localhost:8000/docs`

## Database

The application uses SQLite by default. The database file (`hrms.db`) will be created automatically on first run.

To use PostgreSQL or MySQL, update the `SQLALCHEMY_DATABASE_URL` in `main.py`.

