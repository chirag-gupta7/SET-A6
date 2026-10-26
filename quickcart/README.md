# QuickCart
E-commerce demo (JSON API + minimal HTML pages) for a QA/testing course.

## Run
```
cd quickcart
pip install -r requirements.txt
python app.py
```
API + pages on http://127.0.0.1:5000 (quickcart.db auto-created on first run with seed data).
Pages: /products /login /register /products/<id> /cart /checkout /orders /orders/<id> /profile

Demo login: `test@quickcart.com` / `Test@123`

Tests (server running, fresh DB recommended):
```
python tests/test_api.py
python tests/check_ids.py
```
