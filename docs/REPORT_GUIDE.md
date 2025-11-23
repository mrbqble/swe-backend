# Report Generation Guide

This guide helps you generate all materials needed for the course submission report.

## 📋 Checklist

### 1. OpenAPI Schema Export

Export the final OpenAPI schema:

```bash
# Start the API first
uvicorn app.main:app --reload

# In another terminal, export the schema
make export-openapi
# or
python scripts/export_openapi.py

# The schema will be saved to docs/openapi.json
```

**For Report**: Include `docs/openapi.json` in your submission.

### 2. Swagger UI Screenshots

Take screenshots of the Swagger UI at `http://localhost:8000/docs`:

#### Required Screenshots:

1. **Main Swagger UI Page**
   - Shows all endpoint groups
   - URL: `http://localhost:8000/docs`
   - Capture: Full page showing all tags

2. **Authentication Endpoints**
   - Expand the "auth" tag
   - Show signup, login, refresh endpoints
   - Capture: All three endpoints visible

3. **Product Management Endpoints**
   - Expand the "products" tag
   - Show CRUD operations
   - Capture: POST, PUT, DELETE, GET endpoints

4. **Order Management Endpoints**
   - Expand the "orders" tag
   - Show order creation and status update
   - Capture: POST and PATCH endpoints

5. **Example Request/Response**
   - Click "Try it out" on any endpoint
   - Fill in example data
   - Show request body and response
   - Capture: Request/response example

6. **Schema Examples**
   - Click on any schema (e.g., OrderCreate)
   - Show example values
   - Capture: Schema with example

### 3. Module Write-ups

Module documentation is available in `docs/MODULES.md`. Each module includes:

- **Purpose**: What the module does
- **Key Features**: Main functionality
- **Endpoints**: All API endpoints
- **Data Models**: Database models and relationships
- **Example Flow**: Step-by-step usage

**For Report**: Copy relevant sections from `docs/MODULES.md` for each module you're documenting.

### 4. Demo Script Verification

Verify the demo script matches your presentation flows:

```bash
# Make script executable
chmod +x scripts/demo.sh

# Run the demo (requires API running)
./scripts/demo.sh
```

The demo script covers:
1. Health check
2. Consumer signup/login
3. Consumer link request
4. Supplier login
5. Supplier link approval
6. Supplier product creation
7. Consumer catalog viewing
8. Consumer order creation
9. Supplier order management
10. Chat session creation
11. Complaint creation
12. Complaint resolution

**For Report**: Include the demo script output or screenshots of the demo execution.

### 5. User Account Setup

Create user accounts for demo purposes using the signup endpoint:

```bash
# Create consumer account
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "consumer@example.com", "password": "Password123", "role": "consumer"}'

# Create supplier owner account
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "supplier.owner@example.com", "password": "Password123", "role": "supplier_owner"}'
```

**For Report**: Document the demo accounts created and their purposes.

## 📝 Report Sections

### Suggested Report Structure:

1. **Introduction**
   - Project overview
   - Technology stack
   - Architecture overview

2. **Module Documentation**
   - Use content from `docs/MODULES.md`
   - Include purpose, endpoints, and data models for each module
   - Add diagrams if needed

3. **API Documentation**
   - Include Swagger UI screenshots
   - Reference OpenAPI schema
   - Show example requests/responses

4. **Demo Flows**
   - Consumer flow (signup → link → catalog → order → chat → complaint)
   - Supplier flow (signup → staff → products → links → orders → complaints)
   - Include screenshots or demo script output

5. **Code Quality**
   - Code quality metrics
   - Security scanning results

6. **Deployment & Setup**
   - Reference `docs/SUBMISSION_GUIDE.md`
   - Include setup instructions
   - Docker deployment guide

## 🎯 Key Points for Report

### Architecture Highlights

- **FastAPI**: Modern, fast web framework
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL**: Relational database
- **JWT**: Token-based authentication
- **Pydantic**: Data validation
- **Alembic**: Database migrations

### Security Features

- JWT authentication with refresh tokens
- Bcrypt password hashing (12 rounds)
- Role-based access control (RBAC)
- Input validation and size limits
- Security linting with Bandit


### Observability

- Structured logging with correlation IDs
- Slow query logging
- Health checks with DB status
- Error tracking with stack traces

## 📦 Submission Package

Include in your submission:

1. **Code Repository**
   - Complete source code
   - All documentation files

2. **Documentation**
   - `docs/MODULES.md` - Module documentation
   - `docs/SUBMISSION_GUIDE.md` - Setup guide
   - `docs/FRONTEND_HANDOVER.md` - Integration guide
   - `docs/SECURITY.md` - Security guide
   - `docs/openapi.json` - OpenAPI schema

3. **Screenshots**
   - Swagger UI main page
   - Endpoint groups
   - Example requests/responses
   - Schema examples

4. **Demo Materials**
   - Demo script (`scripts/demo.sh`)
   - Demo script output or video
   - Postman collection (`docs/postman_collection.json`)

5. **Report Document**
   - Written report with all sections
   - Module descriptions
   - API documentation
   - Demo flows

## ✅ Final Checklist

Before submission, verify:

- [ ] API starts successfully
- [ ] OpenAPI schema exported (`make export-openapi`)
- [ ] Swagger screenshots taken
- [ ] Module documentation complete
- [ ] Demo script verified
- [ ] Submission guide reviewed
- [ ] All documentation files included
- [ ] Code quality checks pass (`make check`)

## 🚀 Quick Start for Instructors

Instructors can quickly get started by following `docs/SUBMISSION_GUIDE.md`:

1. Clone repository
2. Install dependencies
3. Set up database
4. Run migrations
6. Start server
7. Access `/docs` for Swagger UI
8. Run demo script

All steps are documented with commands and expected outputs.
