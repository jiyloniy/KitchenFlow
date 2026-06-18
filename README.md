# KitchenFlow API

KitchenFlow is a Django REST API foundation for restaurant and kitchen management.

## Modules

- Dashboard and analytics
- Restaurants, branches and tables
- Orders, POS payments and KDS statuses
- Menu, recipes and ingredients
- Inventory, suppliers and purchases
- CRM, loyalty tiers and bonuses
- Staff and attendance
- AI assistant insights

## Run locally

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open:

- API root: http://127.0.0.1:8000/api/
- Swagger docs: http://127.0.0.1:8000/api/docs/
- Admin: http://127.0.0.1:8000/admin/

## Auth

JWT endpoints:

- `POST /api/auth/token/`
- `POST /api/auth/token/refresh/`

Create an admin user:

```bash
python manage.py createsuperuser
```
# KitchenFlow
