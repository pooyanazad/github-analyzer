# Testing Guide

This project includes a comprehensive test suite with unit tests, quality tests, and smoke tests.

## Test Structure

```
tests/
├── unit/           # Unit tests for individual components
│   ├── test_app.py      # Flask app tests
│   └── test_analyzer.py # GitHub analyzer tests
├── quality/        # Code quality and style tests
│   ├── test_code_quality.py
│   └── test_style_checker.py
└── smoke/          # Integration and smoke tests
    ├── test_basic_functionality.py
    └── test_integration.py
```

## Running Tests

### Quick Test Run
Use the provided test runner script:
```bash
python run_tests.py
```

### Individual Test Suites
```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Quality tests only
python -m pytest tests/quality/ -v

# Smoke tests only
python -m pytest tests/smoke/ -v

# All tests
python -m pytest tests/ -v
```

### With Coverage
```bash
python -m pytest tests/ --cov=. --cov-report=term-missing
```

## CI/CD Pipeline

The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that automatically runs all tests on:
- Push to `main` or `develop` branches
- Pull requests to `main` branch

## Test Types

### Unit Tests (28 tests)
- Test individual functions and methods
- Mock external dependencies
- Fast execution (< 2 seconds)

### Quality Tests (8 tests)
- Basic code structure validation
- Security pattern checks
- Style compliance (simplified)

### Smoke Tests (28 tests)
- Integration testing
- End-to-end workflow validation
- Basic functionality verification

## Test Results

All tests should pass:
- ✅ **64 passed, 2 skipped** in ~6 seconds
- No failing tests
- Comprehensive coverage of core functionality

## Adding New Tests

1. **Unit tests**: Add to `tests/unit/` for new functions/classes
2. **Quality tests**: Add to `tests/quality/` for code standards
3. **Smoke tests**: Add to `tests/smoke/` for integration scenarios

Follow the existing patterns and keep tests simple and fast.