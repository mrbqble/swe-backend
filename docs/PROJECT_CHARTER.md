# Project Charter

## Stack

**Backend Framework:**

- Python 3.13.5+
- FastAPI
- Uvicorn (ASGI server)

**Database:**

- PostgreSQL
- SQLAlchemy 2.x (async)
- Alembic (migrations)

**Validation:**

- Pydantic v2 (data validation)

**Code Quality:**

- Ruff (linter & formatter)
- mypy (static type checking)
- pre-commit (Git hooks)

## Roles

The system defines the following user roles:

- `consumer`: End users who purchase products
- `supplier_owner`: Owners of supplier businesses
- `supplier_manager`: Managers within supplier organizations
- `supplier_sales`: Sales representatives for suppliers
- `admin`: System administrators

## API Versioning

- Base prefix: `/api/v1`
- All endpoints are versioned under this prefix
- Example: `/api/v1/`, `/api/v1/health`

## Error Response Format

All API errors follow this standardized format:

```json
{
  "detail": "string",
  "code": "string",
  "meta": { ... }
}
```

**Fields:**

- `detail`: Human-readable error message
- `code`: Machine-readable error code (e.g., `VALIDATION_ERROR`, `HTTP_404`)
- `meta`: Optional additional error context (e.g., validation details)

**Example:**

```json
{
	"detail": "Validation error",
	"code": "VALIDATION_ERROR",
	"meta": {
		"errors": [
			{
				"loc": ["body", "email"],
				"msg": "value is not a valid email address",
				"type": "value_error.email"
			}
		]
	}
}
```

## Pagination Response Format

All paginated responses follow this standardized format:

```json
{
  "items": [...],
  "page": 1,
  "size": 20,
  "total": 123,
  "pages": 7
}
```

**Fields:**

- `items`: Array of items for the current page
- `page`: Current page number (1-indexed)
- `size`: Number of items per page
- `total`: Total number of items across all pages
- `pages`: Total number of pages

---

**Version:** 1.0 **Date:** 2025.11.17
