# REST API Server (Python FastAPI)

Python FastAPI server for financial data operations.

## Tech Stack
- Python 3.11+
- FastAPI
- PostgreSQL
- Redis (optional)

## Structure
```
restapi-server/
├── services/           # Business logic
├── tests/              # Unit tests
├── server.py           # Entry point
├── requirements.txt
└── README.md
```

## Getting Started

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run development server
```bash
python server.py
```

## Environment Variables
Copy `.env.example` to `.env` and configure:
```
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
REDIS_URL=redis://localhost:6379
```

## API Documentation
Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`
