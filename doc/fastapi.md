# setup
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
