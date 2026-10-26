"""QuickCart end-to-end API test suite (stdlib only, run against a live server).

Run the server first (cd quickcart && python app.py), then: python tests/test_api.py
The suite expects a FRESH database (delete quickcart.db and restart the server).
"""
import datetime
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:5000"


def make_client():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


anon, seed, user, buyer = make_client(), make_client(), make_client(), make_client()
PASS, FAIL = [], []


def call(client, label, method, path, body=None, expect=None):
    req = urllib.request.Request(BASE + path, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    try:
        with client.open(req) as resp:
            status, raw = resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read().decode()
    try:
        payload = json.loads(raw) if raw else {}
    except ValueError:
        payload = raw
    ok = expect is None or status == expect
    (PASS if ok else FAIL).append((label, status, expect, payload))
    return status, payload


def check(label, condition):
    (PASS if condition else FAIL).append((label, "assert", "", {"ok": bool(condition)}))


# wait for the server to come up
deadline = time.time() + 20
while True:
    try:
        urllib.request.urlopen(BASE + "/api/health", timeout=2).read()
        break
    except Exception:
        if time.time() > deadline:
            print("server did not start within 20s")
            sys.exit(1)
        time.sleep(0.3)

# ================= STEP 1 REGRESSION: health / auth / profile / products =================

call(anon, "health", "GET", "/api/health", expect=200)

call(user, "register ok", "POST", "/api/register",
     {"name": "Ram Tester", "email": "ram@test.com", "password": "pass@12"}, expect=201)
call(anon, "register duplicate email -> 409", "POST", "/api/register",
     {"name": "Ram Two", "email": "ram@test.com", "password": "pass@12"}, expect=409)
call(anon, "register bad email -> 400", "POST", "/api/register",
     {"name": "Bad Mail", "email": "not-an-email", "password": "pass@12"}, expect=400)
call(anon, "register short name (1) -> 400", "POST", "/api/register",
     {"name": "A", "email": "a1@test.com", "password": "pass@12"}, expect=400)
call(anon, "register long name (51) -> 400", "POST", "/api/register",
     {"name": "N" * 51, "email": "a2@test.com", "password": "pass@12"}, expect=400)
call(anon, "register short password (5) -> 400", "POST", "/api/register",
     {"name": "Pw Test", "email": "a3@test.com", "password": "12345"}, expect=400)
call(anon, "register long password (21) -> 400", "POST", "/api/register",
     {"name": "Pw Test", "email": "a4@test.com", "password": "1" * 21}, expect=400)
call(anon, "register boundary name (2) -> 201", "POST", "/api/register",
     {"name": "Bo", "email": "b1@test.com", "password": "pass@12"}, expect=201)
call(anon, "register boundary name (50) -> 201", "POST", "/api/register",
     {"name": "N" * 50, "email": "b2@test.com", "password": "pass@12"}, expect=201)
call(anon, "register boundary password (6) -> 201", "POST", "/api/register",
     {"name": "Pw Six", "email": "b3@test.com", "password": "123456"}, expect=201)
call(anon, "register boundary password (20) -> 201", "POST", "/api/register",
     {"name": "Pw Twenty", "email": "b4@test.com", "password": "12345678901234567890"},
     expect=201)

call(seed, "login seed user (Test@123) -> 200", "POST", "/api/login",
     {"email": "test@quickcart.com", "password": "Test@123"}, expect=200)
call(anon, "login wrong password -> 401", "POST", "/api/login",
     {"email": "test@quickcart.com", "password": "wrong"}, expect=401)
call(anon, "login unknown email -> 401", "POST", "/api/login",
     {"email": "ghost@test.com", "password": "pass@12"}, expect=401)
call(user, "login registered user -> 200", "POST", "/api/login",
     {"email": "ram@test.com", "password": "pass@12"}, expect=200)

call(anon, "profile GET anon -> 401", "GET", "/api/profile", expect=401)
call(user, "profile GET -> 200", "GET", "/api/profile", expect=200)
call(user, "profile PUT valid -> 200", "PUT", "/api/profile",
     {"name": "Ram Tester", "phone": "9876543210", "address": "12 MG Road, Pune"}, expect=200)
call(user, "profile PUT phone 9 digits -> 400", "PUT", "/api/profile",
     {"name": "Ram Tester", "phone": "987654321"}, expect=400)
call(user, "profile PUT phone 11 digits -> 400", "PUT", "/api/profile",
     {"name": "Ram Tester", "phone": "98765432101"}, expect=400)
call(user, "profile PUT phone letters -> 400", "PUT", "/api/profile",
     {"name": "Ram Tester", "phone": "12345abcde"}, expect=400)
call(user, "profile PUT short name -> 400", "PUT", "/api/profile",
     {"name": "R"}, expect=400)
call(user, "profile PUT empty phone (optional) -> 200", "PUT", "/api/profile",
     {"name": "Ram Tester", "phone": "", "address": "New Address"}, expect=200)
s, p = call(user, "profile GET after PUT -> 200", "GET", "/api/profile", expect=200)
check("profile PUT persisted", p.get("address") == "New Address" and p.get("phone") is None)

s, p = call(anon, "list all -> 200", "GET", "/api/products", expect=200)
check("12 seeded products", isinstance(p, list) and len(p) == 12)
s, p = call(anon, "search HEAD (case-insensitive)", "GET", "/api/products?search=HEAD", expect=200)
check("search matches 1", len(p) == 1 and p[0]["name"] == "Bluetooth Headphones")
s, p = call(anon, "search no match", "GET", "/api/products?search=zzz", expect=200)
check("search no match empty", len(p) == 0)
call(anon, "min_price not a number -> 400", "GET", "/api/products?min_price=abc", expect=400)
s, p = call(anon, "category Books", "GET", "/api/products?category=Books", expect=200)
check("category Books -> 3", len(p) == 3)
s, p = call(anon, "category books (lowercase)", "GET", "/api/products?category=books", expect=200)
check("category case-insensitive -> 3", len(p) == 3)
s, p = call(anon, "category unknown", "GET", "/api/products?category=Toys", expect=200)
check("category unknown -> 0", len(p) == 0)
s, p = call(anon, "min_price=1000", "GET", "/api/products?min_price=1000", expect=200)
check("min_price -> 4", len(p) == 4)
s, p = call(anon, "max_price=300", "GET", "/api/products?max_price=300", expect=200)
check("max_price -> 4", len(p) == 4)
s, p = call(anon, "min 500 + max 1500", "GET", "/api/products?min_price=500&max_price=1500",
            expect=200)
check("price range -> 4", len(p) == 4)
s, p = call(anon, "sort price_asc", "GET", "/api/products?sort=price_asc", expect=200)
check("price_asc first = 99.0", p and p[0]["price"] == 99.0)
s, p = call(anon, "sort price_desc", "GET", "/api/products?sort=price_desc", expect=200)
check("price_desc first = 5000.0", p and p[0]["price"] == 5000.0)
s, p = call(anon, "sort bogus ignored", "GET", "/api/products?sort=bogus", expect=200)
check("bogus sort -> all 12", len(p) == 12)

s, p = call(anon, "get product 1 -> 200", "GET", "/api/products/1", expect=200)
check("product 1 is USB-C Charging Cable", p.get("name") == "USB-C Charging Cable")
call(anon, "get product 999 -> 404", "GET", "/api/products/999", expect=404)
call(anon, "get product abc -> 404", "GET", "/api/products/abc", expect=404)

call(anon, "create product anon -> 401", "POST", "/api/products",
     {"name": "Nope", "price": 10, "stock": 1}, expect=401)
call(anon, "delete product 1 anon -> 401", "DELETE", "/api/products/1", expect=401)

new = {"name": "Test Tripod", "description": "demo tripod", "category": "Electronics",
       "price": 199.5, "stock": 5, "image_url": "http://example.com/tripod.jpg"}
s, p = call(user, "create product -> 201", "POST", "/api/products", new, expect=201)
pid = p.get("id")
check("created product visible", isinstance(pid, int))

call(user, "create price 0 -> 400", "POST", "/api/products",
     {"name": "Free", "price": 0, "stock": 1}, expect=400)
call(user, "create price negative -> 400", "POST", "/api/products",
     {"name": "Cheap", "price": -5, "stock": 1}, expect=400)
call(user, "create stock negative -> 400", "POST", "/api/products",
     {"name": "Ghost", "price": 10, "stock": -1}, expect=400)
call(user, "create stock float -> 400", "POST", "/api/products",
     {"name": "Half", "price": 10, "stock": 2.5}, expect=400)
call(user, "create stock string -> 400", "POST", "/api/products",
     {"name": "Text", "price": 10, "stock": "5"}, expect=400)
call(user, "create short name -> 400", "POST", "/api/products",
     {"name": "X", "price": 10, "stock": 1}, expect=400)
call(user, "create missing name -> 400", "POST", "/api/products",
     {"price": 10, "stock": 1}, expect=400)

s, p = call(user, "update product -> 200", "PUT", f"/api/products/{pid}",
            {"price": 149.5, "stock": 9}, expect=200)
check("update persisted", p.get("price") == 149.5 and p.get("stock") == 9)
call(user, "update price 0 -> 400", "PUT", f"/api/products/{pid}", {"price": 0}, expect=400)
call(user, "update missing product -> 404", "PUT", "/api/products/999", {"price": 5}, expect=404)
call(user, "delete product -> 200", "DELETE", f"/api/products/{pid}", expect=200)
call(user, "delete again -> 404", "DELETE", f"/api/products/{pid}", expect=404)

s, p = call(user, "create boundary stock 0 -> 201", "POST", "/api/products",
            {"name": "Zero Stock", "price": 1, "stock": 0}, expect=201)
call(user, "cleanup boundary product", "DELETE", f"/api/products/{p['id']}", expect=200)
s, p = call(user, "create boundary name 50 -> 201", "POST", "/api/products",
            {"name": "P" * 50, "price": 1, "stock": 1}, expect=201)
call(user, "cleanup boundary product", "DELETE", f"/api/products/{p['id']}", expect=200)

call(user, "logout -> 200", "POST", "/api/logout", expect=200)
call(user, "profile after logout -> 401", "GET", "/api/profile", expect=401)
call(anon, "unknown route -> 404 json", "GET", "/api/nope", expect=404)

# ================= STEP 2: cart / coupons / checkout / orders =================

TODAY = datetime.date.today()
CUR_EXP = f"{TODAY.month:02d}/{TODAY.year % 100:02d}"
_prev = TODAY.replace(day=1) - datetime.timedelta(days=1)
PAST_EXP = f"{_prev.month:02d}/{_prev.year % 100:02d}"

# owner logs back in and creates coupon/checkout helper products
call(user, "owner re-login -> 200", "POST", "/api/login",
     {"email": "ram@test.com", "password": "pass@12"}, expect=200)
s, p = call(user, "create helper A price 0.01 -> 201", "POST", "/api/products",
            {"name": "Test Penny", "description": "coupon boundary helper",
             "category": "Electronics", "price": 0.01, "stock": 10}, expect=201)
ID_A = p.get("id")
s, p = call(user, "create helper B price 499.99 -> 201", "POST", "/api/products",
            {"name": "Test Big Item", "description": "coupon boundary helper",
             "category": "Electronics", "price": 499.99, "stock": 50}, expect=201)
ID_B = p.get("id")
check("product ids not reused after delete (AUTOINCREMENT)",
      isinstance(ID_A, int) and ID_A > 15 and isinstance(ID_B, int) and ID_B > ID_A)

# ---- anon guardrails on new endpoints ----
call(anon, "cart GET anon -> 401", "GET", "/api/cart", expect=401)
call(anon, "cart add anon -> 401", "POST", "/api/cart/add",
     {"product_id": 1, "quantity": 1}, expect=401)
call(anon, "cart update anon -> 401", "PUT", "/api/cart/update",
     {"product_id": 1, "quantity": 1}, expect=401)
call(anon, "cart remove anon -> 401", "DELETE", "/api/cart/remove/1", expect=401)
call(anon, "coupon apply anon -> 401", "POST", "/api/cart/coupon",
     {"code": "SAVE10"}, expect=401)
call(anon, "coupon remove anon -> 401", "DELETE", "/api/cart/coupon", expect=401)
call(anon, "checkout anon -> 401", "POST", "/api/checkout", {}, expect=401)
call(anon, "orders list anon -> 401", "GET", "/api/orders", expect=401)

# ---- buyer session ----
call(buyer, "register buyer -> 201", "POST", "/api/register",
     {"name": "Priya Buyer", "email": "priya@test.com", "password": "pass@12"}, expect=201)
call(buyer, "login buyer -> 200", "POST", "/api/login",
     {"email": "priya@test.com", "password": "pass@12"}, expect=200)

# ---- empty cart view ----
s, p = call(buyer, "empty cart view -> 200", "GET", "/api/cart", expect=200)
check("cart view keys", isinstance(p, dict) and
      set(p) == {"items", "subtotal", "coupon_code", "discount", "total", "coupon_message"})
check("empty cart values", p.get("items") == [] and p.get("subtotal") == 0
      and p.get("coupon_code") is None and p.get("coupon_message") is None)

# ---- cart add / update / remove + BVA on quantity ----
call(buyer, "add product_id bool -> 400", "POST", "/api/cart/add",
     {"product_id": True, "quantity": 1}, expect=400)
call(buyer, "add product_id string -> 400", "POST", "/api/cart/add",
     {"product_id": "1", "quantity": 1}, expect=400)
call(buyer, "add missing product_id -> 400", "POST", "/api/cart/add",
     {"quantity": 1}, expect=400)
call(buyer, "add quantity 0 -> 400", "POST", "/api/cart/add",
     {"product_id": 1, "quantity": 0}, expect=400)
call(buyer, "add quantity 11 -> 400", "POST", "/api/cart/add",
     {"product_id": 1, "quantity": 11}, expect=400)
call(buyer, "add quantity 2.5 -> 400", "POST", "/api/cart/add",
     {"product_id": 1, "quantity": 2.5}, expect=400)
call(buyer, "add quantity '3' -> 400", "POST", "/api/cart/add",
     {"product_id": 1, "quantity": "3"}, expect=400)
call(buyer, "add quantity -1 -> 400", "POST", "/api/cart/add",
     {"product_id": 1, "quantity": -1}, expect=400)
call(buyer, "add missing quantity -> 400", "POST", "/api/cart/add",
     {"product_id": 1}, expect=400)
call(buyer, "add unknown product -> 404", "POST", "/api/cart/add",
     {"product_id": 999, "quantity": 1}, expect=404)
s, p = call(buyer, "add stock-0 product -> 400", "POST", "/api/cart/add",
            {"product_id": 10, "quantity": 1}, expect=400)
check("stock-0 message", p.get("error") == "out of stock")

s, p = call(buyer, "add USB-C x2 -> 200", "POST", "/api/cart/add",
            {"product_id": 1, "quantity": 2}, expect=200)
check("cart line built", p.get("items") and p["items"][0]["product_id"] == 1
      and p["items"][0]["quantity"] == 2 and p["items"][0]["price"] == 99.0
      and p["items"][0]["line_total"] == 198.0 and p["subtotal"] == 198.0)

call(buyer, "add more 1 -> 200 (qty 3)", "POST", "/api/cart/add",
     {"product_id": 1, "quantity": 1}, expect=200)
s, p = call(buyer, "add more 8 -> 400 (>10)", "POST", "/api/cart/add",
            {"product_id": 1, "quantity": 8}, expect=400)
s, p = call(buyer, "add more 7 -> 200 (qty 10)", "POST", "/api/cart/add",
            {"product_id": 1, "quantity": 7}, expect=200)
check("accumulated qty 10 boundary", p.get("items") and p["items"][0]["quantity"] == 10)
s, p = call(buyer, "add more 1 -> 400 at cap", "POST", "/api/cart/add",
            {"product_id": 1, "quantity": 1}, expect=400)
check("cap message mentions 10", "10" in str(p.get("error")))
call(buyer, "update to 1 -> 200", "PUT", "/api/cart/update",
     {"product_id": 1, "quantity": 1}, expect=200)

call(buyer, "update unknown product -> 404", "PUT", "/api/cart/update",
     {"product_id": 999, "quantity": 1}, expect=404)
call(buyer, "update product not in cart -> 404", "PUT", "/api/cart/update",
     {"product_id": 2, "quantity": 1}, expect=404)
call(buyer, "update quantity 11 -> 400", "PUT", "/api/cart/update",
     {"product_id": 1, "quantity": 11}, expect=400)
call(buyer, "update quantity 0 -> 400", "PUT", "/api/cart/update",
     {"product_id": 1, "quantity": 0}, expect=400)

# stock boundary on Study Chair (id 12, stock 3)
call(buyer, "add chair qty 3 == stock -> 200", "POST", "/api/cart/add",
     {"product_id": 12, "quantity": 3}, expect=200)
s, p = call(buyer, "add chair qty 1 more -> 400 (>stock)", "POST", "/api/cart/add",
            {"product_id": 12, "quantity": 1}, expect=400)
check("stock cap message mentions 3", "3" in str(p.get("error")))
call(buyer, "update chair qty 4 -> 400", "PUT", "/api/cart/update",
     {"product_id": 12, "quantity": 4}, expect=400)
call(buyer, "update chair qty 3 == stock -> 200", "PUT", "/api/cart/update",
     {"product_id": 12, "quantity": 3}, expect=200)
call(buyer, "remove chair -> 200", "DELETE", "/api/cart/remove/12", expect=200)
call(buyer, "remove chair again -> 404", "DELETE", "/api/cart/remove/12", expect=404)
call(buyer, "remove unknown product -> 404", "DELETE", "/api/cart/remove/999", expect=404)
call(buyer, "clear cart -> 200", "DELETE", "/api/cart/remove/1", expect=200)

# ---- coupons ----
call(buyer, "apply coupon no code -> 400", "POST", "/api/cart/coupon", {}, expect=400)
call(buyer, "unknown coupon -> 404", "POST", "/api/cart/coupon",
     {"code": "NOSUCH"}, expect=404)
s, p = call(buyer, "expired coupon -> 400", "POST", "/api/cart/coupon",
            {"code": "old50"}, expect=400)
check("expired message", p.get("error") == "coupon expired")
s, p = call(buyer, "SAVE10 on empty cart -> 400", "POST", "/api/cart/coupon",
            {"code": "save10"}, expect=400)
check("min order message", p.get("error") == "minimum order of 500 required")
s, p = call(buyer, "cart after failed apply -> no coupon", "GET", "/api/cart", expect=200)
check("no coupon applied after failures", p.get("coupon_code") is None
      and p.get("coupon_message") is None)

call(buyer, "add big item -> 200", "POST", "/api/cart/add",
     {"product_id": ID_B, "quantity": 1}, expect=200)
# subtotal 499.99: boundary below min_order 500
call(buyer, "SAVE10 at 499.99 -> 400", "POST", "/api/cart/coupon",
     {"code": "save10"}, expect=400)
call(buyer, "add penny -> 200", "POST", "/api/cart/add",
     {"product_id": ID_A, "quantity": 1}, expect=200)
# subtotal exactly 500.00 == min_order -> valid (exact boundary); also tests trim/case
s, p = call(buyer, "SAVE10 at 500.00 -> 200", "POST", "/api/cart/coupon",
            {"code": "  save10 "}, expect=200)
check("SAVE10 math at 500.00", p.get("coupon_code") == "SAVE10"
      and p.get("discount") == 50.0 and p.get("total") == 450.0)
s, p = call(buyer, "remove penny -> 200", "DELETE", f"/api/cart/remove/{ID_A}", expect=200)
check("drop message at transition", p.get("coupon_code") is None
      and p.get("coupon_message") == "minimum order of 500 required")
s, p = call(buyer, "cart after subtotal drop", "GET", "/api/cart", expect=200)
check("coupon dropped with message", p.get("coupon_code") is None
      and p.get("coupon_message") == "minimum order of 500 required")

call(buyer, "re-add penny -> 200", "POST", "/api/cart/add",
     {"product_id": ID_A, "quantity": 1}, expect=200)
call(buyer, "re-apply SAVE10 -> 200", "POST", "/api/cart/coupon",
     {"code": "SAVE10"}, expect=200)
call(buyer, "penny qty 2 -> 200", "PUT", "/api/cart/update",
     {"product_id": ID_A, "quantity": 2}, expect=200)
# subtotal 500.01: above boundary; 10% = 50.001 rounds to 50.00
s, p = call(buyer, "cart at 500.01 -> discount 50.0", "GET", "/api/cart", expect=200)
check("SAVE10 at 500.01", p.get("discount") == 50.0 and p.get("total") == 450.01
      and p.get("coupon_message") is None)

call(buyer, "FLAT100 below min -> 400", "POST", "/api/cart/coupon",
     {"code": "flat100"}, expect=400)
s, p = call(buyer, "cart after failed FLAT100", "GET", "/api/cart", expect=200)
check("failed apply keeps old coupon", p.get("coupon_code") == "SAVE10")
call(buyer, "big item qty 3 -> 200", "PUT", "/api/cart/update",
     {"product_id": ID_B, "quantity": 3}, expect=200)
# subtotal 1499.99
s, p = call(buyer, "FLAT100 applied -> 200", "POST", "/api/cart/coupon",
            {"code": "FLAT100"}, expect=200)
check("FLAT100 replaces SAVE10", p.get("coupon_code") == "FLAT100"
      and p.get("discount") == 100.0 and p.get("total") == 1399.99)
s, p = call(buyer, "WELCOME20 replaces -> 200", "POST", "/api/cart/coupon",
            {"code": "welcome20"}, expect=200)
check("WELCOME20 math", p.get("coupon_code") == "WELCOME20"
      and p.get("discount") == 300.0 and p.get("total") == 1199.99)
call(buyer, "remove coupon -> 200", "DELETE", "/api/cart/coupon", expect=200)
call(buyer, "remove coupon again -> 404", "DELETE", "/api/cart/coupon", expect=404)
call(buyer, "clear cart (penny) -> 200", "DELETE", f"/api/cart/remove/{ID_A}", expect=200)
call(buyer, "clear cart (big item) -> 200", "DELETE", f"/api/cart/remove/{ID_B}", expect=200)
call(user, "delete helper A -> 200", "DELETE", f"/api/products/{ID_A}", expect=200)
call(user, "delete helper B -> 200", "DELETE", f"/api/products/{ID_B}", expect=200)

# ---- checkout validation ----
VALID = {"shipping_address": "12 MG Road, Pune 411001", "name_on_card": "Priya Buyer",
         "card_number": "4001234567891234", "expiry": CUR_EXP, "cvv": "123"}


def checkout_with(overrides, expect, label):
    return call(buyer, label, "POST", "/api/checkout", {**VALID, **overrides}, expect=expect)


call(buyer, "checkout empty cart -> 400", "POST", "/api/checkout", {}, expect=400)

call(buyer, "add USB-C x2 for checkout -> 200", "POST", "/api/cart/add",
     {"product_id": 1, "quantity": 2}, expect=200)

checkout_with({"shipping_address": "123456789"}, 400, "address 9 chars -> 400")
checkout_with({"shipping_address": "X" * 201}, 400, "address 201 chars -> 400")
checkout_with({"name_on_card": "A"}, 400, "name_on_card 1 char -> 400")
checkout_with({"card_number": "123456789012345"}, 400, "card 15 digits -> 400")
checkout_with({"card_number": "12345678901234567"}, 400, "card 17 digits -> 400")
checkout_with({"card_number": "1234 5678 9012 345a"}, 400, "card with letters -> 400")
checkout_with({"expiry": "13/26"}, 400, "expiry month 13 -> 400")
checkout_with({"expiry": "9/26"}, 400, "expiry format M/YY -> 400")
checkout_with({"expiry": "ab/26"}, 400, "expiry garbage -> 400")
checkout_with({"expiry": PAST_EXP}, 400, "expiry past month -> 400")
checkout_with({"cvv": "12"}, 400, "cvv 2 digits -> 400")
checkout_with({"cvv": "1234"}, 400, "cvv 4 digits -> 400")

# stock re-check at checkout
s, p = call(user, "create stock-check helper -> 201", "POST", "/api/products",
            {"name": "Test Sofa", "description": "stock recheck helper", "category": "Home",
             "price": 50, "stock": 2}, expect=201)
SID = p.get("id")
call(buyer, "add sofa x2 -> 200", "POST", "/api/cart/add",
     {"product_id": SID, "quantity": 2}, expect=200)
call(user, "owner drops sofa stock to 1 -> 200", "PUT", f"/api/products/{SID}",
     {"stock": 1}, expect=200)
s, p = checkout_with({}, 400, "checkout insufficient stock -> 400")
check("stock error names product", "Test Sofa" in str(p.get("error")))
call(buyer, "remove sofa -> 200", "DELETE", f"/api/cart/remove/{SID}", expect=200)
call(user, "owner deletes sofa -> 200", "DELETE", f"/api/products/{SID}", expect=200)

# declined card leaves everything unchanged
checkout_with({"card_number": "4000000000000002"}, 402, "declined card -> 402")
checkout_with({"card_number": "4000 0000 0000 0002"}, 402, "declined card w/ spaces -> 402")
s, p = call(buyer, "cart unchanged after declines", "GET", "/api/cart", expect=200)
check("cart intact after declines", p.get("items") and p["items"][0]["quantity"] == 2
      and p.get("subtotal") == 198.0 and p.get("coupon_code") is None)
s, p = call(buyer, "no orders after declines", "GET", "/api/orders", expect=200)
check("orders empty", p == [])

# successful checkout; spaces in card number are stripped
s, p = checkout_with({"card_number": "4000 0000 0000 0001", "cvv": "789"}, 201,
                     "checkout success -> 201")
O1 = p.get("id")
check("order totals", p.get("subtotal") == 198.0 and p.get("discount") == 0.0
      and p.get("total") == 198.0)
check("order header", p.get("status") == "Placed" and p.get("coupon_code") is None
      and p.get("card_last4") == "0001"
      and p.get("shipping_address") == "12 MG Road, Pune 411001")
check("order created_at present", isinstance(p.get("created_at"), str)
      and len(p.get("created_at", "")) >= 19)
check("order items snapshot", isinstance(p.get("items"), list)
      and len(p["items"]) == 1 and p["items"][0] == {
          "product_id": 1, "product_name": "USB-C Charging Cable",
          "price": 99.0, "quantity": 2})

s, p = call(anon, "stock reduced after checkout", "GET", "/api/products/1", expect=200)
check("stock 40 -> 38", p.get("stock") == 38)
s, p = call(buyer, "cart cleared after checkout", "GET", "/api/cart", expect=200)
check("cart empty + coupon cleared", p.get("items") == [] and p.get("coupon_code") is None)

# ---- orders ----
s, p = call(buyer, "orders list -> 1 order", "GET", "/api/orders", expect=200)
check("orders newest first", len(p) == 1 and p[0]["id"] == O1)
s, p = call(buyer, "get own order -> 200", "GET", f"/api/orders/{O1}", expect=200)
check("own order payload", p.get("id") == O1 and isinstance(p.get("items"), list)
      and len(p["items"]) == 1)
call(user, "other user's order -> 404", "GET", f"/api/orders/{O1}", expect=404)
call(buyer, "unknown order -> 404", "GET", "/api/orders/999", expect=404)

s, p = call(buyer, "status Placed->Packed -> 200", "PUT", f"/api/orders/{O1}/status",
            {"status": "Packed"}, expect=200)
check("status persisted", p.get("status") == "Packed")
call(buyer, "bad status -> 400", "PUT", f"/api/orders/{O1}/status",
     {"status": "Flew"}, expect=400)
call(user, "status change on others' order -> 404", "PUT", f"/api/orders/{O1}/status",
     {"status": "Shipped"}, expect=404)
call(anon, "status change anon -> 401", "PUT", f"/api/orders/{O1}/status",
     {"status": "Shipped"}, expect=401)

# coupon flows through checkout end-to-end
call(buyer, "add USB-C x1 -> 200", "POST", "/api/cart/add",
     {"product_id": 1, "quantity": 1}, expect=200)
s, p = call(buyer, "apply WELCOME20 -> 200", "POST", "/api/cart/coupon",
            {"code": "welcome20"}, expect=200)
check("WELCOME20 on small cart", p.get("discount") == 19.8 and p.get("total") == 79.2)
s, p = checkout_with({"card_number": "4111111111111111", "cvv": "321"}, 201,
                     "checkout with coupon -> 201")
O2 = p.get("id")
check("coupon order totals", p.get("subtotal") == 99.0 and p.get("discount") == 19.8
      and p.get("total") == 79.2 and p.get("coupon_code") == "WELCOME20"
      and p.get("card_last4") == "1111" and p.get("status") == "Placed")
s, p = call(anon, "stock after second checkout", "GET", "/api/products/1", expect=200)
check("stock 38 -> 37", p.get("stock") == 37)
s, p = call(buyer, "coupon cleared after checkout", "GET", "/api/cart", expect=200)
check("cart coupon_code null", p.get("coupon_code") is None)
s, p = call(buyer, "orders newest first [O2, O1]", "GET", "/api/orders", expect=200)
check("two orders, newest first", len(p) == 2 and p[0]["id"] == O2 and p[1]["id"] == O1)

# ---- summary ----
print(f"PASS: {len(PASS)}   FAIL: {len(FAIL)}")
for label, status, expect, payload in FAIL:
    print(f"FAIL: {label}  (status={status}, expect={expect})")
    print(f"      {json.dumps(payload)[:300]}")
sys.exit(1 if FAIL else 0)
