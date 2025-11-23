# Submission Guide for Instructors

This guide provides step-by-step instructions for instructors to run and evaluate the B2B Supplier-Wholesale Exchange Platform API.

## 🚀 Quick Start

### Prerequisites

- Python 3.13.5 or higher
- PostgreSQL 12+ (or Docker for containerized setup)
- Git

### Option 1: Local Setup (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd swe-backend

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp env.example .env
# Edit .env with your database credentials

# 5. Run migrations
alembic upgrade head

# 6. Seed database
python scripts/seed.py

# 7. Start the server
uvicorn app.main:app --reload
```

### Option 2: Docker Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd swe-backend

# 2. Start services
docker compose up -d

# 3. Wait for services to be healthy (check logs)
docker compose logs -f

# 4. Seed database (in container)
docker compose exec app python scripts/seed.py
```

## ✅ Verification Steps

### 1. Health Check

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "env": "dev",
  "db": "ok"
}
```

### 2. OpenAPI Documentation

Open in browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 3. Verify Authentication

```bash
# Login with seeded consumer
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "consumer@example.com",
    "password": "Password123"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## 📋 Seeded Data

After running `python scripts/seed.py`, the following sample accounts are available:

### Users

| Email | Password | Role |
|-------|----------|------|
| `consumer@example.com` | `Password123` | Consumer |
| `supplier.owner@example.com` | `Password123` | Supplier Owner |
| `supplier.manager@example.com` | `Password123` | Supplier Manager |
| `supplier.sales@example.com` | `Password123` | Supplier Sales |

### Data

- **1 Supplier**: "Acme Wholesale Supplies"
- **3 Products**: Premium Widget A, Standard Widget B, Economy Widget C
- **1 Link**: Consumer ↔ Supplier (ACCEPTED status)
- **1 Order**: Pending order with 2 items

## 🎬 Demo Scripts

### Automated Demo

Run the complete demo script:

```bash
# Make script executable (Linux/Mac)
chmod +x scripts/demo.sh

# Run demo
./scripts/demo.sh

# Or using make
make demo
```

**Note**: The demo script requires:
- API running on http://localhost:8000
- Database seeded
- `jq` installed for JSON parsing (optional, for pretty output)

### Manual Demo Flow

Follow these steps to manually verify the complete flow:

#### Consumer Flow

1. **Signup/Login**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "consumer@example.com", "password": "Password123"}'
   ```
   Save the `access_token` from response.

2. **View Links** (should see accepted link)
   ```bash
   curl -X GET http://localhost:8000/api/v1/links \
     -H "Authorization: Bearer <access_token>"
   ```

3. **View Catalog**
   ```bash
   curl -X GET http://localhost:8000/api/v1/catalog/suppliers/1/products \
     -H "Authorization: Bearer <access_token>"
   ```

4. **Create Order**
   ```bash
   curl -X POST http://localhost:8000/api/v1/orders \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "supplier_id": 1,
       "items": [{"product_id": 1, "qty": 5}]
     }'
   ```

5. **Create Chat Session**
   ```bash
   curl -X POST http://localhost:8000/api/v1/chats/sessions \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"sales_rep_id": 3, "order_id": 1}'
   ```

#### Supplier Flow

1. **Login as Supplier Owner**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "supplier.owner@example.com", "password": "Password123"}'
   ```
   Save the `access_token`.

2. **View Products**
   ```bash
   curl -X GET http://localhost:8000/api/v1/products \
     -H "Authorization: Bearer <access_token>"
   ```

3. **Create Product**
   ```bash
   curl -X POST http://localhost:8000/api/v1/products \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "New Product",
       "price_kzt": "25000.00",
       "currency": "KZT",
       "sku": "NEW-001",
       "stock_qty": 100,
       "is_active": true
     }'
   ```

4. **View Orders**
   ```bash
   curl -X GET http://localhost:8000/api/v1/orders \
     -H "Authorization: Bearer <access_token>"
   ```

5. **Update Order Status**
   ```bash
   curl -X PATCH http://localhost:8000/api/v1/orders/1/status \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"status": "accepted"}'
   ```

## 📊 Module Verification Checklist

### ✅ Authentication Module
- [ ] Signup creates user and returns tokens
- [ ] Login authenticates and returns tokens
- [ ] Refresh token generates new access token
- [ ] Invalid credentials return 401

### ✅ Link Management Module
- [ ] Consumer can request link
- [ ] Supplier owner can approve/deny link
- [ ] Link status transitions correctly
- [ ] Catalog access requires accepted link

### ✅ Product Management Module
- [ ] Supplier owner/manager can create products
- [ ] Products can be updated
- [ ] Products can be deleted (owner only)
- [ ] SKU uniqueness enforced per supplier

### ✅ Order Management Module
- [ ] Consumer can create orders
- [ ] Order total calculated correctly
- [ ] Supplier can view orders
- [ ] Order status can be updated
- [ ] Status transitions follow state machine

### ✅ Chat Module
- [ ] Consumer can create chat sessions
- [ ] Participants can send messages
- [ ] Messages are paginated
- [ ] Access control enforced

### ✅ Complaint Module
- [ ] Consumer can file complaints
- [ ] Sales rep/manager can update status
- [ ] Resolution required for resolved status
- [ ] Status transitions follow state machine

## 📁 Project Structure

```
swe-backend/
├── app/
│   ├── api/              # API routes
│   ├── core/             # Core functionality (config, security, etc.)
│   ├── db/               # Database session
│   ├── modules/          # Business logic modules
│   │   ├── auth/        # Authentication
│   │   ├── user/        # User management
│   │   ├── link/        # Link management
│   │   ├── product/     # Product management
│   │   ├── order/       # Order management
│   │   ├── chat/        # Chat system
│   │   ├── complaint/   # Complaint management
│   │   └── notification/ # Notifications
│   └── schemas/         # Pydantic schemas
├── alembic/             # Database migrations
├── docs/               # Documentation
│   ├── MODULES.md      # Module documentation
│   ├── FRONTEND_HANDOVER.md
│   ├── SECURITY.md
│   └── postman_collection.json
├── scripts/            # Utility scripts
│   ├── seed.py         # Database seeding
│   ├── demo.sh         # Demo script
│   └── export_openapi.py
├── requirements.txt    # Dependencies
├── pyproject.toml     # Tool configuration
└── README.md          # Main documentation
```

## 🔍 Code Quality Checks

Run all quality checks:

```bash
make check
# or
./scripts.ps1 check  # Windows PowerShell
```

This runs:
- Linting (ruff)
- Formatting (ruff format)
- Type checking (mypy)
- Security scanning (bandit)

## 📝 Documentation

- **Module Documentation**: `docs/MODULES.md` - Detailed module descriptions
- **Frontend Handover**: `docs/FRONTEND_HANDOVER.md` - Integration guide
- **Security Guide**: `docs/SECURITY.md` - Security practices
- **Postman Collection**: `docs/postman_collection.json` - API collection

## 🐛 Troubleshooting

### Database Connection Issues

```bash
# Check database is running
psql -U postgres -d postgres -c "SELECT 1;"

# Check connection string in .env
cat .env | grep DATABASE_URL
```

### Migration Issues

```bash
# Check migration status
alembic current

# Reset migrations (development only)
alembic downgrade base
alembic upgrade head
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill process or change port in .env
```

## 📞 Support

For issues or questions:
1. Check the logs: `docker compose logs` or server console
2. Review error messages (include correlation IDs)
3. Check OpenAPI docs at `/docs` for endpoint details
4. Review module documentation in `docs/MODULES.md`

## ✅ Acceptance Criteria

The API meets all acceptance criteria if:

- [x] API starts successfully
- [x] Health check returns `{"status": "ok", "db": "ok"}`
- [x] Database can be seeded with `python scripts/seed.py`
- [x] All seeded users can log in
- [x] Consumer flow works: login → view catalog → place order
- [x] Supplier flow works: login → manage products → manage orders
- [x] OpenAPI docs accessible at `/docs`
- [x] All endpoints return expected responses
- [x] Error handling works correctly
