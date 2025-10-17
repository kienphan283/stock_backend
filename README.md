# Stock Backend

Backend services for Snow Analytics Stock platform.

---

## 📁 Structure

```
stock_backend/
├── src/                    # Express.js API (TypeScript)
│   ├── index.ts
│   ├── controllers/
│   ├── routes/
│   └── services/
│
├── etl/                    # Python FastAPI + Data Services
│   ├── server.py           # FastAPI main server
│   ├── requirements.txt    # Python dependencies
│   ├── services/           # Data processing services
│   └── tests/              # Python tests
│
├── package.json
├── tsconfig.json
└── README.md              # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Node.js 18+**
- **PostgreSQL 15+**
- **Redis 5.0+** (optional)

### Installation

#### 1. Install Python Dependencies (ETL)

```bash
cd etl
pip install -r requirements.txt
```

**What gets installed:**

- `fastapi==0.104.1` - Modern web framework
- `uvicorn[standard]==0.24.0` - ASGI server
- `psycopg2-binary==2.9.9` - PostgreSQL adapter
- `redis==5.0.1` - Redis client (optional)
- `python-dotenv==1.0.0` - Environment variables

**Installation tips:**

```bash
# Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

cd etl
pip install -r requirements.txt

# Or install globally
pip install -r etl/requirements.txt

# Verify installation
python -c "import fastapi; print(fastapi.__version__)"
```

#### 2. Install Node.js Dependencies (Optional Express API)

```bash
npm install
# or
pnpm install
```

**What gets installed:**

- `express` - Web framework
- `cors` - CORS middleware
- `helmet` - Security middleware
- `morgan` - HTTP request logger

---

## 🗄️ Database Setup

### Step 1: Create Database

```bash
psql -U postgres
```

```sql
CREATE DATABASE Web_quan_li_danh_muc;
\c Web_quan_li_danh_muc
```

### Step 2: Run Schema

From project root:

```bash
psql -U postgres -d Web_quan_li_danh_muc -f sql/Database.sql
```

### Step 3: Import Financial Data

```bash
cd etl
python services/data.py
```

**Configuration:**
Edit `services/data.py` to change company:

```python
SYMBOL = "IBM"        # Change to desired ticker
API_KEY = "your_key"  # Alpha Vantage API key
```

---

## 🏃 Running

### Option 1: Python API Only

```bash
cd etl
python server.py

# Or with uvicorn
uvicorn server:app --reload --port 8000
```

**Endpoints:**

- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- Health: http://localhost:8000

### Option 2: Express API (Optional)

```bash
npm run dev
```

Runs on http://localhost:3001

---

## 📡 API Documentation

### Python FastAPI

#### GET /api/financials

Fetch multi-period financial statements.

**Parameters:**

- `company` (required): Ticker symbol (e.g., "IBM")
- `type` (required): Statement type - "IS", "BS", or "CF"
- `period` (required): Period type - "annual" or "quarterly"

**Example:**

```bash
curl "http://localhost:8000/api/financials?company=IBM&type=IS&period=quarterly"
```

**Response:**

```json
{
  "company": "IBM",
  "type": "IS",
  "period": "quarterly",
  "periods": ["2025-Q2", "2025-Q1", ...],
  "data": {
    "Total Revenue": {
      "2025-Q2": 16977000000.0,
      "2025-Q1": 14541000000.0
    }
  }
}
```

**Interactive Docs:** http://localhost:8000/docs

---

## 🔧 Configuration

### Python API

**File:** `etl/server.py`

```python
# Database
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "Web_quan_li_danh_muc",
    "user": "postgres",
    "password": "123456"  # Change this!
}

# Redis (optional)
REDIS_CLIENT = redis.Redis(
    host='localhost',
    port=6379,
    db=0
)
```

### Environment Variables

Create `.env` in project root:

```env
FINNHUB_API_KEY=your_api_key_here
ALPHA_VANTAGE_KEY=your_key_here
```

---

## 🧪 Testing

### Python Tests

```bash
cd etl

# Run specific test
python tests/simple_test.py
python tests/test_financials_api.py

# Run all with pytest
pytest tests/
```

### Test API

```bash
# Test endpoint
curl "http://localhost:8000/api/financials?company=IBM&type=IS&period=quarterly"

# Check health
curl http://localhost:8000
```

---

## 🐛 Troubleshooting

### psycopg2 Installation Failed

**Windows:**

```bash
pip install psycopg2-binary --no-cache-dir
```

**Linux:**

```bash
sudo apt-get install libpq-dev python3-dev
pip install psycopg2-binary
```

**Mac:**

```bash
brew install postgresql
pip install psycopg2-binary
```

### Database Connection Error

**Check PostgreSQL:**

```bash
pg_isready
sudo systemctl status postgresql
```

**Test connection:**

```bash
psql -U postgres -d Web_quan_li_danh_muc
```

### Port 8000 Already in Use

**Windows:**

```bash
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Linux/Mac:**

```bash
lsof -ti:8000 | xargs kill -9
```

### Module Import Errors

Make sure you're in the `etl/` directory:

```bash
cd etl
python server.py
```

Or add to PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/etl"
python etl/server.py
```

---

## 📦 ETL Package Details

### services/data_loader.py

Legacy CSV data loader for Finnhub data.

**Usage:**

```python
from services.data_loader import StockDataLoader

loader = StockDataLoader(data_dir="./data")
quote = loader.get_quote()
profile = loader.get_company_profile()
```

### services/fetch_finnhub_data.py

Fetch real-time data from Finnhub API.

**Usage:**

```bash
cd etl
python services/fetch_finnhub_data.py
```

**Requirements:**

- Finnhub API key in `.env`
- Rate limit: 60 calls/minute

### services/data.py

Import financial data from Alpha Vantage to PostgreSQL.

**Usage:**

```bash
cd etl
python services/data.py
```

**Configuration:**

```python
SYMBOL = "IBM"  # Change company
API_KEY = "..."  # Alpha Vantage key
```

---

## 📝 Development

### Code Style

- Python: PEP 8
- Use type hints
- Add docstrings

### Adding New Endpoints

1. Edit `etl/server.py`
2. Add Pydantic models
3. Add route handler
4. Add tests in `etl/tests/`
5. Update Swagger docs

### Virtual Environment (Recommended)

```bash
# Create venv
python -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
cd etl
pip install -r requirements.txt

# Deactivate when done
deactivate
```

---

## 🔗 Related Documentation

- [Main README](../README.md) - Project overview
- [Frontend README](../stock_frontend/README.md) - Frontend setup
- [ETL README](etl/README.md) - Detailed ETL documentation
- [Database Schema](../sql/Database.sql) - PostgreSQL schema

---

## ✅ Checklist

Before running backend:

- [ ] Python 3.8+ installed
- [ ] PostgreSQL running
- [ ] Database created
- [ ] Schema loaded (`sql/Database.sql`)
- [ ] Financial data imported
- [ ] Python packages installed (`pip install -r etl/requirements.txt`)
- [ ] Redis running (optional)
- [ ] API key configured (if needed)

---

**Ready to integrate with frontend at http://localhost:3000**
