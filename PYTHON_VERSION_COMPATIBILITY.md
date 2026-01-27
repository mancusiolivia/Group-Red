# Python Version Compatibility

This project is compatible with **Python 3.11** and **Python 3.13+** (tested on 3.11.0+ and 3.13.0+).

## Tested Versions

- Python 3.11.x
- Python 3.13.x

## Dependencies

All dependencies in `server/requirements.txt` are compatible with both Python 3.11 and 3.13:

- **FastAPI** >= 0.115.0 (supports Python 3.11+)
- **SQLAlchemy** >= 2.0.0, < 3.0.0 (supports Python 3.11+)
- **Pydantic** >= 2.9.0 (supports Python 3.11+)
- **Uvicorn** >= 0.32.0 (supports Python 3.11+)

## Compatibility Notes

### Database Models

The database models use `utc_now()` helper function instead of `datetime.utcnow()` directly in default parameters to ensure compatibility across versions.

### Code Compatibility

- All code uses features available in Python 3.11+
- Type hints are compatible with both versions
- No Python 3.12+ specific syntax (like `match/case` with guards) is used

## Installation

The same `requirements.txt` works for both versions:

```bash
pip install -r server/requirements.txt
```

## Testing

To verify your Python version:

```bash
python --version
```

Should show Python 3.11.x or 3.13.x

## Known Issues

- None currently - all features work on both versions
- `datetime.utcnow()` is deprecated in Python 3.12+ but still functions correctly (the code uses a helper function to maintain compatibility)
