# run all
docker-compose up --build

# run one by one
frontend : 
    npm create vite@latest frontend -- --template react
    cd frontend
    npm install
    npm install react-router-dom

    npm run dev

backend  : 
    python3 -m venv venv
    venv/Scripts/activate
    pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv
    pip install python-jose passlib[bcrypt]
    pip freeze > requirements.txt
    uvicorn app.main:app --reload


