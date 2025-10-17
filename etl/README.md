# ETL (Extract, Transform, Load)

Python-based data processing and API server for Stock Analytics.

## Structure

```
etl/
├── server.py              # FastAPI server (main entry point)
├── requirements.txt       # Python dependencies
│
├── services/              # Data services
│   ├── data_loader.py     # CSV data loader (legacy)
│   ├── data.py            # Alpha Vantage data importer
│   └── fetch_finnhub_data.py  # Finnhub API fetcher
│
└── tests/                 # Unit & integration tests
    ├── test_data_loader.py
    ├── test_financials_api.py
    └── simple_test.py
```

## Quick Start

### 1. Install Dependencies

```bash
cd stock_backend/etl
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in project root:

```env
FINNHUB_API_KEY=your_api_key_here
```

### 3. Start FastAPI Server

```bash
cd stock_backend/etl
python server.py
```

Or use uvicorn:

```bash
cd stock_backend/etl
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at:

- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000

## API Endpoints

### GET /api/financials

Fetch financial data with pivoted format.

**Parameters:**

- `company` (required): Company ticker symbol (e.g., "IBM")
- `type` (required): Statement type - "IS", "BS", or "CF"
- `period` (required): Period type - "annual" or "quarterly"

**Example:**

```bash
curl "http://localhost:8000/api/financials?company=IBM&type=IS&period=quarterly"
```

## Database Configuration

Edit `server.py` to update database connection:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "Web_quan_li_danh_muc",
    "user": "postgres",
    "password": "123456"
}
```

## Redis Caching (Optional)

Redis is optional but recommended for performance:

```bash
# Install Redis (Windows)
# Download from: https://github.com/microsoftarchive/redis/releases

# Start Redis
redis-server
```

If Redis is not available, the server will work without caching.

## Testing

Run all tests:

```bash
cd stock_backend/etl
python -m pytest tests/
```

Run specific test:

```bash
python tests/test_financials_api.py
```

## Data Import

### Import from Alpha Vantage

```bash
cd stock_backend/etl
python services/data.py
```

Edit `services/data.py` to change company:

```python
SYMBOL = "IBM"  # Change this
```

### Fetch from Finnhub

```bash
cd stock_backend/etl
python services/fetch_finnhub_data.py
```

## Development

### Code Style

- Follow PEP 8
- Use type hints where possible
- Add docstrings to functions

### Adding New Endpoints

1. Add route in `server.py`
2. Add Pydantic model for validation
3. Add tests in `tests/`
4. Update Swagger docs

## Troubleshooting

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Database Connection Failed

- Check PostgreSQL is running
- Verify DB_CONFIG credentials
- Ensure database exists

### Import Errors

Make sure you're in the `etl/` directory when running scripts, or use:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## Related Documentation

- [Main Documentation](../../docs/README.md)
- [API Documentation](../../docs/02-API-DOCUMENTATION.md)
- [Architecture](../../docs/04-ARCHITECTURE.md)
