# Definition of Done (DoD)

This document defines the criteria that must be met for any backend work to be considered complete and ready for deployment.

## Code Quality

### ✅ Linting & Formatting

- [ ] All code passes **Ruff** linter checks
- [ ] Code is formatted with **Ruff** formatter
- [ ] No linting warnings or errors
- [ ] Pre-commit hooks run successfully

### ✅ Type Checking

- [ ] **mypy** type checking passes with no errors
- [ ] All functions have proper type hints
- [ ] All return types are explicitly defined
- [ ] Type stubs are provided where necessary

### ✅ Code Standards

- [ ] Code follows PEP 8 style guidelines
- [ ] Meaningful variable and function names
- [ ] Functions are focused and do one thing
- [ ] No hardcoded values (use configuration)
- [ ] No commented-out code or debug statements
- [ ] Proper docstrings for all public functions and classes

## API Standards

### ✅ Endpoint Requirements

- [ ] All endpoints follow `/api/v1` versioning prefix
- [ ] Request/response models use Pydantic schemas
- [ ] Error responses follow standard format: `{"detail": str, "code": str, "meta": {...}}`
- [ ] Paginated responses follow standard format: `{"items": [...], "page": 1, "size": 20, "total": 123, "pages": 7}`
- [ ] Appropriate HTTP status codes are used
- [ ] Endpoints have proper OpenAPI/Swagger documentation

### ✅ Validation

- [ ] Input validation using Pydantic models
- [ ] Validation errors return standardized error format
- [ ] Database constraints are properly handled
- [ ] Business logic validation is implemented

## Database

### ✅ Migrations

- [ ] Database migrations created with **Alembic**
- [ ] Migration files are reviewed and verified
- [ ] Both `upgrade` and `downgrade` paths work
- [ ] Migration rollback has been verified
- [ ] No raw SQL in application code (use SQLAlchemy ORM)

### ✅ Database Operations

- [ ] All database queries use async SQLAlchemy
- [ ] Database sessions are properly managed
- [ ] Connection pooling is configured correctly
- [ ] Transactions are used where appropriate

## Security

### ✅ Security Checklist

- [ ] No sensitive data in code or logs
- [ ] Environment variables used for secrets
- [ ] SQL injection prevention (using ORM parameterized queries)
- [ ] Input sanitization and validation
- [ ] Proper authentication/authorization (if applicable)
- [ ] CORS configured appropriately (if applicable)
- [ ] Rate limiting considered (if applicable)

## Documentation

### ✅ Code Documentation

- [ ] Docstrings for all public functions/classes
- [ ] Complex logic has inline comments
- [ ] API endpoints documented in code (OpenAPI)
- [ ] README updated if needed

### ✅ Project Documentation

- [ ] PROJECT_CHARTER.md aligns with changes (if applicable)
- [ ] Configuration changes documented
- [ ] Breaking changes documented
- [ ] Migration steps documented (if applicable)

## Review & Merge

### ✅ Code Review

- [ ] Code reviewed by at least one other team member
- [ ] All review comments addressed
- [ ] Code follows project architecture patterns
- [ ] No conflicts with main branch

### ✅ Pre-Merge Checklist

- [ ] All CI/CD checks pass
- [ ] Pre-commit hooks installed and passing
- [ ] Branch is up to date with main
- [ ] No merge conflicts
- [ ] Pull request description is clear and complete

## Performance

### ✅ Performance Considerations

- [ ] Database queries are optimized (no N+1 queries)
- [ ] Appropriate use of async/await
- [ ] Pagination implemented for list endpoints
- [ ] Response times are acceptable
- [ ] Memory usage is reasonable

## Logging & Monitoring

### ✅ Logging

- [ ] Appropriate logging levels used (DEBUG, INFO, WARNING, ERROR)
- [ ] Sensitive information not logged
- [ ] Error logs include sufficient context
- [ ] Structured logging follows project standards

## Deployment

### ✅ Deployment Readiness

- [ ] Code works in local development environment
- [ ] Code works in staging environment (if applicable)
- [ ] Environment variables documented
- [ ] Database migrations verified in staging
- [ ] Rollback plan prepared (if applicable)

---

**Note:** This DoD should be checked for every pull request, feature, or bug fix before considering work complete.

**Version:** 1.0
**Date:** 2025.11.17
