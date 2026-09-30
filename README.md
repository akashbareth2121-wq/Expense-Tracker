# Expense Tracker (Flask)

## 🚀 Live Demo

| Project             | Live Link                                       |
| ------------------- | ----------------------------------------------- |
| **Expense Tracker** | [**Open Live Project →**](https://expense-tracker-gdq7.onrender.com) |

## Run locally

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                                      # http://127.0.0.1:5000
```

Add a few categories first (Categories > Add Category), then add expenses.

## Deploy on Render (free live link)

1. Push this folder to a GitHub repo (`.gitignore` already excludes the database).
2. Render > New > Web Service > connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Environment variables: `SECRET_KEY` = a long random string, `FLASK_DEBUG` = `0`.
6. Data persistence: the free disk resets on redeploy. For lasting data, create a free Render PostgreSQL database and set `DATABASE_URL` to its URL (already supported).

## Deploy on PythonAnywhere

1. Upload the files, create a virtualenv, `pip install -r requirements.txt`.
2. Web tab > Add new web app > Flask; point the WSGI file at `from app import app as application`.
3. Set `SECRET_KEY` in the WSGI file via `os.environ`. SQLite persists there.
