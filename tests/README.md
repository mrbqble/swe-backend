# Unit Tests

This directory contains unit tests for the application.

## Structure

- `conftest.py` - Pytest configuration and shared fixtures
- `test_main_root.py` - Tests for root endpoint (GET /)
- `test_main_health.py` - Tests for health check endpoint (GET /health)
- `test_auth_signup.py` - Tests for authentication signup route
- `test_auth_login.py` - Tests for authentication login route
- `test_auth_refresh.py` - Tests for authentication refresh token route
- `test_user_me.py` - Tests for user get_me route
- `test_notifications_get.py` - Tests for GET /notifications route
- `test_notifications_mark_read.py` - Tests for PATCH /notifications/{id}/read route
- `test_catalog_get.py` - Tests for GET /catalog route
- `test_catalog_suppliers.py` - Tests for GET /catalog/suppliers route
- `test_links_create.py` - Tests for POST /links/requests route
- `test_links_update_status.py` - Tests for PATCH /links/{id}/status route
- `test_links_get_incoming.py` - Tests for GET /links/incoming route
- `test_links_get_single.py` - Tests for GET /links/{id} route
- `test_links_get.py` - Tests for GET /links route
- `test_suppliers_me_get.py` - Tests for GET /suppliers/me route
- `test_suppliers_me_put.py` - Tests for PUT /suppliers/me route
- `test_suppliers_me_deactivate.py` - Tests for PATCH /suppliers/me/deactivate route
- `test_suppliers_me_delete.py` - Tests for DELETE /suppliers/me route
- `test_suppliers_staff_get.py` - Tests for GET /suppliers/staff route
- `test_suppliers_staff_post.py` - Tests for POST /suppliers/staff route
- `test_suppliers_staff_delete.py` - Tests for DELETE /suppliers/staff/{staff_id} route
- `test_suppliers_staff_deactivate.py` - Tests for PATCH /suppliers/staff/{staff_id}/deactivate route
- `test_products_get.py` - Tests for GET /products route (public list)
- `test_products_get_single.py` - Tests for GET /products/{product_id} route (public get)
- `test_products_create.py` - Tests for POST /products route
- `test_products_update.py` - Tests for PUT /products/{product_id} route
- `test_products_delete.py` - Tests for DELETE /products/{product_id} route
- `test_products_me_get.py` - Tests for GET /products/me route

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_main_root.py
pytest tests/test_main_health.py
pytest tests/test_auth_signup.py
pytest tests/test_auth_login.py
pytest tests/test_auth_refresh.py
pytest tests/test_user_me.py
pytest tests/test_notifications_get.py
pytest tests/test_notifications_mark_read.py
pytest tests/test_catalog_get.py
pytest tests/test_catalog_suppliers.py
pytest tests/test_links_create.py
pytest tests/test_links_update_status.py
pytest tests/test_links_get_incoming.py
pytest tests/test_links_get_single.py
pytest tests/test_links_get.py
pytest tests/test_suppliers_me_get.py
pytest tests/test_suppliers_me_put.py
pytest tests/test_suppliers_me_deactivate.py
pytest tests/test_suppliers_me_delete.py
pytest tests/test_suppliers_staff_get.py
pytest tests/test_suppliers_staff_post.py
pytest tests/test_suppliers_staff_delete.py
pytest tests/test_suppliers_staff_deactivate.py
pytest tests/test_products_get.py
pytest tests/test_products_get_single.py
pytest tests/test_products_create.py
pytest tests/test_products_update.py
pytest tests/test_products_delete.py
pytest tests/test_products_me_get.py
```

### Run with verbose output
```bash
pytest -v
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run specific test
```bash
pytest tests/test_auth_signup.py::TestSignup::test_signup_success_consumer
```

## Test Coverage

### Main Routes

#### Root Endpoint (`test_main_root.py`)
- ✅ Successful root endpoint response

#### Health Check Endpoint (`test_main_health.py`)
- ✅ Health check with healthy database
- ✅ Health check with database connection error
- ✅ Health check with database timeout
- ✅ Health check with database connection exception
- ✅ Health check with database execute error

### Authentication Routes

#### Signup Endpoint (`test_auth_signup.py`)
- ✅ Successful consumer signup
- ✅ Successful supplier owner signup
- ✅ Email already registered error
- ✅ Invalid password (too short)
- ✅ Invalid password (no uppercase)
- ✅ Invalid password (no digit)
- ✅ Signup with custom organization name

#### Login Endpoint (`test_auth_login.py`)
- ✅ Successful login
- ✅ User not found error
- ✅ Incorrect password error
- ✅ Inactive user error

#### Refresh Endpoint (`test_auth_refresh.py`)
- ✅ Successful token refresh
- ✅ Invalid token error
- ✅ Expired token error
- ✅ User not found error
- ✅ Inactive user error
- ✅ Access token instead of refresh token error

### User Routes

#### Get Me Endpoint (`test_user_me.py`)
- ✅ Successful retrieval of current user
- ✅ No token error
- ✅ Invalid token error
- ✅ Expired token error
- ✅ User not found error
- ✅ Inactive user error
- ✅ Different user roles

### Notification Routes

#### Get Notifications Endpoint (`test_notifications_get.py`)
- ✅ Successful retrieval of notifications
- ✅ Filter by read status
- ✅ Pagination support
- ✅ No token error
- ✅ Invalid token error
- ✅ Empty list when no notifications

#### Mark Notification Read Endpoint (`test_notifications_mark_read.py`)
- ✅ Successful marking as read
- ✅ Notification not found error
- ✅ Wrong recipient error
- ✅ No token error
- ✅ Invalid token error
- ✅ Already read notification (idempotent)

### Catalog Routes

#### Get Catalog Endpoint (`test_catalog_get.py`)
- ✅ Successful retrieval of catalog
- ✅ Non-consumer role error
- ✅ Consumer profile not found error
- ✅ Supplier not found error
- ✅ No accepted link error
- ✅ Pagination support
- ✅ No token error

#### List Suppliers Endpoint (`test_catalog_suppliers.py`)
- ✅ Successful listing of suppliers
- ✅ Search query support
- ✅ Pagination support
- ✅ Empty list when no suppliers
- ✅ Public endpoint (no auth required)

### Link Routes

#### Create Link Request Endpoint (`test_links_create.py`)
- ✅ Successful creation of link request
- ✅ Non-consumer role error
- ✅ Consumer profile not found error
- ✅ Supplier not found error
- ✅ Link already exists error
- ✅ No token error

#### Update Link Status Endpoint (`test_links_update_status.py`)
- ✅ Successful update of link status
- ✅ Non-supplier role error
- ✅ Link not found error
- ✅ Invalid state transition error
- ✅ No permission error

#### Get Incoming Links Endpoint (`test_links_get_incoming.py`)
- ✅ Successful retrieval of incoming links
- ✅ Filter by status
- ✅ Non-supplier role error
- ✅ Supplier profile not found error
- ✅ Pagination support

#### Get Single Link Endpoint (`test_links_get_single.py`)
- ✅ Successful retrieval by consumer
- ✅ Successful retrieval by supplier owner
- ✅ Link not found error
- ✅ No permission error

#### Get Consumer Links Endpoint (`test_links_get.py`)
- ✅ Successful retrieval of consumer links
- ✅ Filter by status
- ✅ Non-consumer role error
- ✅ Consumer profile not found error
- ✅ Pagination support

### Supplier Routes

#### Get My Supplier Endpoint (`test_suppliers_me_get.py`)
- ✅ Successful retrieval of supplier profile
- ✅ Supplier profile not found error
- ✅ Non-supplier-owner role error
- ✅ No token error

#### Update My Supplier Endpoint (`test_suppliers_me_put.py`)
- ✅ Successful update of supplier profile
- ✅ Partial update support
- ✅ Supplier profile not found error
- ✅ Non-supplier-owner role error
- ✅ No token error

#### Deactivate My Supplier Endpoint (`test_suppliers_me_deactivate.py`)
- ✅ Successful deactivation of supplier account
- ✅ Supplier profile not found error
- ✅ Non-supplier-owner role error
- ✅ No token error

#### Delete My Supplier Endpoint (`test_suppliers_me_delete.py`)
- ✅ Successful deletion of supplier account
- ✅ Supplier profile not found error
- ✅ Non-supplier-owner role error
- ✅ No token error

#### Get Supplier Staff Endpoint (`test_suppliers_staff_get.py`)
- ✅ Successful retrieval of staff list as owner
- ✅ Successful retrieval of staff list as manager
- ✅ Non-authorized role error
- ✅ Supplier not found error
- ✅ No token error

#### Create Supplier Staff Endpoint (`test_suppliers_staff_post.py`)
- ✅ Successful creation (returns message)
- ✅ Supplier profile not found error
- ✅ Non-owner role error
- ✅ No token error

#### Delete Supplier Staff Endpoint (`test_suppliers_staff_delete.py`)
- ✅ Successful deletion of staff member
- ✅ Staff member not found error
- ✅ Supplier profile not found error
- ✅ Non-owner role error
- ✅ No token error

#### Deactivate Supplier Staff Endpoint (`test_suppliers_staff_deactivate.py`)
- ✅ Successful deactivation of staff member
- ✅ Staff member not found error
- ✅ Supplier profile not found error
- ✅ Non-owner role error
- ✅ No token error

### Product Routes

#### Get Products Endpoint (`test_products_get.py`)
- ✅ Successful retrieval of products list
- ✅ Filter by supplier ID
- ✅ Filter by active status
- ✅ Pagination support
- ✅ Empty list when no products
- ✅ Public endpoint (no auth required)

#### Get Single Product Endpoint (`test_products_get_single.py`)
- ✅ Successful retrieval of a single product
- ✅ Product not found error
- ✅ Includes supplier information
- ✅ Public endpoint (no auth required)

#### Create Product Endpoint (`test_products_create.py`)
- ✅ Successful creation of a product
- ✅ SKU already exists error
- ✅ Supplier profile not found error
- ✅ Non-authorized role error
- ✅ No token error

#### Update Product Endpoint (`test_products_update.py`)
- ✅ Successful update of a product
- ✅ SKU conflict error
- ✅ Product not found error
- ✅ No permission error
- ✅ Non-authorized role error
- ✅ No token error

#### Delete Product Endpoint (`test_products_delete.py`)
- ✅ Successful deletion of a product
- ✅ Product not found error
- ✅ No permission error
- ✅ Non-authorized role error
- ✅ No token error

#### Get My Products Endpoint (`test_products_me_get.py`)
- ✅ Successful retrieval of my products
- ✅ Filter by active status
- ✅ Supplier profile not found error
- ✅ Non-authorized role error
- ✅ Pagination support
- ✅ No token error

## Fixtures

The `conftest.py` file provides the following fixtures:

- `event_loop` - Event loop for async tests
- `mock_db_session` - Mock database session
- `test_client` - FastAPI test client
- `sample_user` - Sample active consumer user
- `sample_inactive_user` - Sample inactive user
- `sample_supplier_owner` - Sample supplier owner user
- `sample_consumer` - Sample consumer profile
- `mock_get_db` - Mock get_db dependency
- `override_get_db` - Override get_db dependency in app

## Notes

- All tests use mocked database sessions to avoid requiring a real database
- JWT tokens are created using the actual security functions for realistic testing
- Tests cover both success and error scenarios
- All tests are isolated and can run independently
