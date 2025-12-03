# Refactoring Guide - New Project Structure

This document explains the new project structure and how to use it.

## New Directory Structure

```
Phase-2/
├── src/                          # Main application source
│   ├── api/                      # API layer
│   │   ├── main.py              # FastAPI app (formerly api.py)
│   │   ├── schemas.py           # Pydantic request/response models
│   │   └── routes/              # API routes (future: split endpoints)
│   │
│   ├── core/                    # Core business logic
│   │   ├── config.py            # Settings & configuration
│   │   ├── database.py          # Database setup
│   │   ├── models.py            # SQLAlchemy models
│   │   └── auth.py              # Authentication logic
│   │
│   ├── crud/                    # CRUD operations (organized by entity)
│   │   ├── package.py           # Package CRUD
│   │   ├── user.py              # User CRUD
│   │   ├── metrics.py           # Metrics CRUD
│   │   ├── rating.py            # Rating CRUD
│   │   ├── download.py          # Download history CRUD
│   │   ├── confusion.py         # Package confusion detection
│   │   └── system.py            # System operations
│   │
│   ├── services/                # Business logic services
│   │   ├── s3_service.py        # S3 operations (formerly s3_helper.py)
│   │   └── metrics_service.py   # Metrics evaluation (formerly metrics_evaluator.py)
│   │
│   ├── utils/                   # Utilities and helpers
│   │   ├── logger.py            # Logging setup (formerly logger_config.py)
│   │   ├── metric_calculators.py
│   │   └── data_fetcher.py
│   │
│   └── cli/                     # Command-line interface
│       ├── gui.py               # GUI application
│       └── init_db.py           # DB initialization script
│
├── tests/                       # All tests
│   ├── test_api_crud.py
│   └── test.py
│
├── scripts/                     # Deployment & utility scripts
│   ├── after_install.sh
│   ├── before_install.sh
│   └── ...
│
├── docs/                        # Documentation
│   ├── API_README.md
│   ├── GUI_README.md
│   ├── TESTING_GUIDE.md
│   └── CRUD_IMPLEMENTATION_PLAN.md
│
├── front-end/                   # Frontend app
│   └── model-registry-frontend/
│
├── requirements.txt             # Python dependencies (new!)
├── .env.example
├── README.md
└── Dockerfile
```

## What Changed

### File Movements

| Old Location | New Location | Notes |
|-------------|-------------|-------|
| `api.py` | `src/api/main.py` | Main FastAPI application |
| `config.py` | `src/core/config.py` | Configuration |
| `database.py` | `src/core/database.py` | Database setup |
| `models.py` | `src/core/models.py` | SQLAlchemy models |
| `auth.py` | `src/core/auth.py` | Authentication |
| `crud.py` | `src/crud/` (split into modules) | Now organized by entity |
| `s3_helper.py` | `src/services/s3_service.py` | S3 operations |
| `metrics_evaluator.py` | `src/services/metrics_service.py` | Metrics evaluation |
| `logger_config.py` | `src/utils/logger.py` | Logging setup |
| `metric_calculators.py` | `src/utils/metric_calculators.py` | Metric calculators |
| `data_fetcher.py` | `src/utils/data_fetcher.py` | Data fetching |
| `gui.py` | `src/cli/gui.py` | GUI application |
| `init_db.py` | `src/cli/init_db.py` | DB initialization |
| `*.md` docs | `docs/` | All documentation |

### Import Changes

All imports have been updated to use the new structure:

**Before:**
```python
from database import get_db
from models import User, Package
from auth import get_current_user
import crud
from config import settings
```

**After:**
```python
from src.core.database import get_db
from src.core.models import User, Package
from src.core.auth import get_current_user
import src.crud as crud
from src.core.config import settings
```

## How to Use the New Structure

### Running the API

Use the new run script:
```bash
./run_api_new.sh
```

Or directly:
```bash
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Initializing the Database

Use the new run script:
```bash
./run_init_db.sh
```

Or directly:
```bash
python3 -m src.cli.init_db
```

### Installing Dependencies

Use the new requirements.txt:
```bash
pip install -r requirements.txt
```

### Running Tests

Tests still work the same way:
```bash
pytest tests/
```

## Benefits of the New Structure

1. **Clear Separation of Concerns**: API, business logic, utilities, and CLI are clearly separated
2. **Better Scalability**: Easy to add new features without cluttering
3. **Improved Navigation**: "Where's the user endpoint?" → `src/api/main.py` (or future `src/api/routes/users.py`)
4. **Professional**: Matches Django, Flask, FastAPI best practices
5. **Cleaner Imports**: `from src.core.config import settings` is more explicit
6. **Easier Testing**: Import from `src.crud.package` instead of `crud`

## Future Improvements

- Split `src/api/main.py` into separate route files in `src/api/routes/`
- Add more comprehensive tests
- Consider adding a `src/api/dependencies.py` for common FastAPI dependencies

## Backward Compatibility

The old files still exist in the root directory for now. They will be removed once testing confirms everything works with the new structure.

## Migration Checklist

- [x] Create new directory structure
- [x] Move and update core files
- [x] Move and update CRUD operations
- [x] Move and update services
- [x] Move and update utilities
- [x] Move and update CLI files
- [x] Create new run scripts
- [x] Create requirements.txt
- [ ] Test all functionality
- [ ] Remove old files
- [ ] Update CI/CD pipelines if needed
