#Orqestra Connect

## Changing models:

modify apex.py

## Pipeline:

docker-compose up -d
run seed_database.py
run contradiction_detection.py

run run_batch_test.py

boot up fast api
/Users/sabharishhh/Developer/orqestra_connect/.venv/bin/python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

frontend: http://localhost:5173
backend: http://localhost:8000/docs


in a parallel terminal:
docker exec -it orqestra_connect-backend-1 python src/scripts/seed_database.py