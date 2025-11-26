# Database Seeding Scripts

This directory contains database seeding scripts for all tables in the application. Each table has its own dedicated seed file that can be run independently or as part of the complete seeding process.

## Structure

The seeding scripts are organized to respect database dependencies, ensuring that parent tables are seeded before child tables:

1. **seed_users.py** - Seeds users table (base table, no dependencies)
2. **seed_suppliers.py** - Seeds suppliers (depends on users)
3. **seed_consumers.py** - Seeds consumers (depends on users)
4. **seed_supplier_staff.py** - Seeds supplier staff (depends on users and suppliers)
5. **seed_products.py** - Seeds products (depends on suppliers)
6. **seed_links.py** - Seeds links (depends on consumers and suppliers). Chat sessions are automatically created when links are accepted.
7. **seed_orders.py** - Seeds orders (depends on suppliers and consumers). Posts structured messages to chat when orders are created.
8. **seed_order_items.py** - Seeds order items (depends on orders and products)
9. **seed_chat_messages.py** - Seeds chat messages (depends on chat sessions and users)
10. **seed_chat_message_attachments.py** - Seeds chat message attachments (depends on chat messages)
11. **seed_complaints.py** - Seeds complaints (depends on orders, consumers, users). Posts structured messages to chat when complaints are created.

## Usage

### Seed All Tables

To seed all tables in the correct order:

```bash
python -m scripts.seed.seed_all
```

Or from the project root:

```bash
python scripts/seed/seed_all.py
```

### Seed Individual Tables

Each seed script can be run independently. For example:

```bash
# Seed only users
python scripts/seed/seed_users.py

# Seed only products (will automatically seed dependencies if needed)
python scripts/seed/seed_products.py
```

Note: When running individual scripts, they will attempt to seed their dependencies automatically if they don't exist.

## Seeded Data

### Users

The seeding creates users with various roles:
- **Supplier Owners**: `supplier1@example.com`, `supplier2@example.com`, `supplier3@example.com` / `Supplier123!`
- **Supplier Managers**: `manager1@example.com`, `manager2@example.com` / `Manager123!`
- **Supplier Sales Reps**: `sales1@example.com`, `sales2@example.com`, `sales3@example.com` / `Sales123!`
- **Consumers**: `consumer1@example.com`, `consumer2@example.com`, `consumer3@example.com`, `consumer4@example.com` / `Consumer123!`
- **Inactive User**: `inactive@example.com` / `Inactive123!` (for testing)

### Suppliers

- Tech Supplies Co.
- Global Merchandise Ltd.
- Premium Products Inc.

### Consumers

- Retail Chain ABC
- Wholesale Distributor XYZ
- Supermarket Network 123
- Department Store Group

### Products

Each supplier has multiple products with realistic data including:
- Product names, descriptions, prices (in KZT)
- SKU codes
- Stock quantities
- Active/inactive status

### Orders

Multiple orders with various statuses:
- Pending
- Accepted
- In Progress
- Completed
- Rejected

### Other Data

- **Links**: Various link statuses (pending, accepted, denied, blocked, unlinked)
- **Chat Sessions**: Automatically created when links are accepted (1-to-1 relationship: one consumer = one sales rep per supplier)
- **Chat Messages**: Realistic conversation threads, including structured messages for orders and complaints
- **Complaints**: Various complaint statuses (open, escalated, resolved)
- **Notifications**: Created automatically by the system when orders/complaints are created/updated, chat messages are sent, or links are accepted/denied

## Safety Features

- **Idempotent**: Each seed script checks if data already exists before seeding
- **Transaction Safety**: All operations are wrapped in database transactions
- **Error Handling**: Proper error handling with rollback on failure
- **Dependency Management**: Scripts handle dependencies automatically

## Notes

- All passwords follow the application's password policy
- Dates are set to realistic timestamps (some in the past for testing)
- The seeding respects all foreign key constraints
- Unique constraints are respected (e.g., email uniqueness)
