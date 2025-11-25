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
Copy the project-wide `.env.example` to `.env` and configure at minimum:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=Web_quan_li_danh_muc
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
REDIS_HOST=localhost
REDIS_PORT=6379
```
Alternatively supply a single `DATABASE_URL=postgresql://user:pass@host:port/dbname`.

## API Documentation
Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`
