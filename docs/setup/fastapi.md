# Basic Setup
python -m venv venv, activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv
pip install python-jose passlib[bcrypt]
pip freeze > requirements.txt
create clean project structure
    backend/
    ├── app/
    │   ├── main.py
    │   ├── database.py
    │   ├── models/
    │   ├── schemas/
    │   ├── routes/
    │   └── core/
    ├── requirements.txt


# (cmd)
- install python
- create env : python3 -m venv .venv
- source .venv/bin/activate (linux) @ .venv/Scripts/Activate.ps1 (windows)
- python3 -m pip install --upgrade pip
- python3 -m pip install -r requirements.txt

- db migration
	install alembic first : python -m pip install alembic OR sudo apt install alembic (for system wide is installed on global system)
	alembic revision --autogenerate -m "initial schema"
	python -m alembic upgrade head OR alembic upgrade head (if alembic is installed on global)

- python3 -m uvicorn app.main:app --reload





(Cookies/Refresh Tokens)
- Development
    COOKIE_SAMESITE = "lax" # send cookies to same app, ex localhost:5173 -> localhost:8000
    COOKIE_SECURE = False

- Production
    COOKIE_SAMESITE = "none" # send cookies to diff app (cross-site), ex https://app.mycompany.com -> https://api.mycompany.com
    COOKIE_SECURE = True
