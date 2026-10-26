"""QuickCart demo API - Flask + plain sqlite3, session-cookie login."""
import datetime
import re
import sqlite3

from flask import Flask, jsonify, redirect, render_template, request, session
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db, init_db

app = Flask(__name__)
# fixed key so session cookies stay valid across server restarts while testing
app.secret_key = "quickcart-demo-secret-key"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\d{10}$")
CARD_RE = re.compile(r"^\d{16}$")
CVV_RE = re.compile(r"^\d{3}$")
EXPIRY_RE = re.compile(r"^\d{2}/\d{2}$")

ORDER_STATUSES = ("Placed", "Packed", "Shipped", "Delivered")
DECLINED_CARD = "4000000000000002"
PRODUCT_EXTRA_FIELDS = ("description", "category", "image_url")

init_db()


def err(message, code):
    return jsonify({"error": message}), code


@app.errorhandler(HTTPException)
def http_error(e):
    # framework errors (404, 405, ...) match the API's own JSON error shape
    return jsonify({"error": e.description}), e.code


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = get_db()
    user = conn.execute(
        "SELECT id, name, email, phone, address FROM users WHERE id = ?", (uid,)
    ).fetchone()
    conn.close()
    return user


def require_login():
    user = current_user()
    if user is None:
        return None, err("login required", 401)
    return user, None


def fmt_money(value):
    value = float(value)
    return str(int(value)) if value.is_integer() else f"{value:.2f}"


# ---------- health ----------

@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


# ---------- auth ----------

@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    if not (2 <= len(name) <= 50):
        return err("name must be 2 to 50 characters", 400)
    if not EMAIL_RE.match(email):
        return err("invalid email format", 400)
    if not (6 <= len(password) <= 20):
        return err("password must be 6 to 20 characters", 400)

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return err("email already registered", 409)
    user = conn.execute(
        "SELECT id, name, email, phone, address FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return jsonify(dict(user)), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if user is None or not check_password_hash(user["password_hash"], password):
        return err("invalid email or password", 401)
    session["user_id"] = user["id"]
    return jsonify({"message": "login successful"})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "logged out"})


# ---------- profile ----------

@app.get("/api/profile")
def get_profile():
    user = current_user()
    if user is None:
        return err("login required", 401)
    return jsonify(dict(user))


@app.put("/api/profile")
def update_profile():
    user = current_user()
    if user is None:
        return err("login required", 401)
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    phone = str(data.get("phone") or "").strip()
    address = str(data.get("address") or "").strip()

    if not (2 <= len(name) <= 50):
        return err("name must be 2 to 50 characters", 400)
    if phone and not PHONE_RE.match(phone):
        return err("phone must be exactly 10 digits", 400)

    conn = get_db()
    conn.execute(
        "UPDATE users SET name = ?, phone = ?, address = ? WHERE id = ?",
        (name, phone or None, address, user["id"]),
    )
    conn.commit()
    updated = conn.execute(
        "SELECT id, name, email, phone, address FROM users WHERE id = ?", (user["id"],)
    ).fetchone()
    conn.close()
    return jsonify(dict(updated))


# ---------- products ----------

def validate_product(data, creating):
    """Returns (error_message, validated_values)."""
    values = {}
    if creating or "name" in data:
        name = str(data.get("name") or "").strip()
        if not (2 <= len(name) <= 50):
            return "name is required and must be 2 to 50 characters", None
        values["name"] = name
    if creating or "price" in data:
        price = data.get("price")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
            return "price must be a number greater than 0", None
        values["price"] = float(price)
    if creating or "stock" in data:
        stock = data.get("stock")
        # bool is a subclass of int, so exclude it explicitly
        if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
            return "stock must be an integer >= 0", None
        values["stock"] = stock
    for key in PRODUCT_EXTRA_FIELDS:
        if key in data:
            values[key] = data[key]
    return None, values


@app.get("/api/products")
def list_products():
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    search = request.args.get("search", "").strip()
    if search:
        like = f"%{search.lower()}%"
        query += " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ?)"
        params += [like, like]

    category = request.args.get("category", "").strip()
    if category:
        query += " AND LOWER(category) = LOWER(?)"
        params.append(category)

    for key, op in (("min_price", ">="), ("max_price", "<=")):
        value = request.args.get(key)
        if value:
            try:
                params.append(float(value))
            except ValueError:
                return err(f"{key} must be a number", 400)
            query += f" AND price {op} ?"

    sort = request.args.get("sort")
    if sort == "price_asc":
        query += " ORDER BY price ASC"
    elif sort == "price_desc":
        query += " ORDER BY price DESC"

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.get("/api/products/<int:product_id>")
def get_product(product_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    if row is None:
        return err("product not found", 404)
    return jsonify(dict(row))


@app.post("/api/products")
def create_product():
    user, error = require_login()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    error, values = validate_product(data, creating=True)
    if error:
        return err(error, 400)
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    conn = get_db()
    cursor = conn.execute(
        f"INSERT INTO products ({columns}) VALUES ({placeholders})", list(values.values())
    )
    conn.commit()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.put("/api/products/<int:product_id>")
def update_product(product_id):
    user, error = require_login()
    if error:
        return error
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        conn.close()
        return err("product not found", 404)
    data = request.get_json(silent=True) or {}
    error, values = validate_product(data, creating=False)
    if error:
        conn.close()
        return err(error, 400)
    if values:
        # column names come only from fixed keys, not user input
        assignments = ", ".join(f"{key} = ?" for key in values)
        conn.execute(f"UPDATE products SET {assignments} WHERE id = ?",
                     [*values.values(), product_id])
        conn.commit()
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.delete("/api/products/<int:product_id>")
def delete_product(product_id):
    user, error = require_login()
    if error:
        return error
    conn = get_db()
    row = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        conn.close()
        return err("product not found", 404)
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "product deleted", "id": product_id})


# ---------- cart ----------

def quantity_error(quantity):
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 10:
        return "quantity must be an integer between 1 and 10"
    return None


def product_id_error(product_id):
    if isinstance(product_id, bool) or not isinstance(product_id, int):
        return "product_id must be an integer"
    return None


def load_cart(conn, user_id):
    """Returns (items, subtotal, rows); rows keep stock for checkout re-checks."""
    rows = conn.execute(
        "SELECT c.product_id, c.quantity, p.name, p.price, p.stock"
        " FROM cart_items c JOIN products p ON p.id = c.product_id"
        " WHERE c.user_id = ? ORDER BY c.product_id",
        (user_id,),
    ).fetchall()
    items = []
    subtotal = 0.0
    for row in rows:
        line_total = round(row["price"] * row["quantity"], 2)
        items.append({
            "product_id": row["product_id"],
            "name": row["name"],
            "price": row["price"],
            "quantity": row["quantity"],
            "line_total": line_total,
        })
        subtotal += line_total
    return items, round(subtotal, 2), rows


def coupon_reject_reason(coupon, subtotal):
    today = datetime.date.today().isoformat()
    if coupon["expires_on"] and coupon["expires_on"] < today:
        return "coupon expired"
    if subtotal < coupon["min_order"]:
        return f"minimum order of {fmt_money(coupon['min_order'])} required"
    return None


def evaluate_coupon(conn, user_id, subtotal):
    """Re-validates the applied coupon on every totals calculation.

    A coupon that becomes invalid stays stored but inactive (no discount); the
    reason is persisted in applied_coupons.drop_message and returned as
    coupon_message on every subsequent cart view until it is re-applied,
    removed, or consumed at checkout. Returns (coupon_row_or_None, discount,
    message).
    """
    row = conn.execute(
        "SELECT code, drop_message FROM applied_coupons WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None, 0.0, None
    coupon = conn.execute(
        "SELECT * FROM coupons WHERE code = ?", (row["code"],)
    ).fetchone()
    reason = "invalid coupon" if coupon is None else coupon_reject_reason(coupon, subtotal)
    if reason is not None:
        if row["drop_message"] != reason:
            conn.execute(
                "UPDATE applied_coupons SET drop_message = ? WHERE user_id = ?",
                (reason, user_id),
            )
        return None, 0.0, reason
    if row["drop_message"]:
        conn.execute(
            "UPDATE applied_coupons SET drop_message = NULL WHERE user_id = ?", (user_id,)
        )
    if coupon["type"] == "percent":
        discount = subtotal * coupon["value"] / 100
    else:
        discount = coupon["value"]
    discount = round(min(discount, subtotal), 2)
    return coupon, discount, None


def cart_view(conn, user_id):
    items, subtotal, _ = load_cart(conn, user_id)
    coupon, discount, message = evaluate_coupon(conn, user_id, subtotal)
    return {
        "items": items,
        "subtotal": subtotal,
        "coupon_code": coupon["code"] if coupon else None,
        "discount": discount,
        "total": round(subtotal - discount, 2),
        "coupon_message": message,
    }


@app.get("/api/cart")
def get_cart():
    user, error = require_login()
    if error:
        return error
    conn = get_db()
    view = cart_view(conn, user["id"])
    conn.commit()  # a coupon dropped during re-validation must persist
    conn.close()
    return jsonify(view)


@app.post("/api/cart/add")
def cart_add():
    user, error = require_login()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity")
    error = quantity_error(quantity) or product_id_error(product_id)
    if error:
        return err(error, 400)
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        return err("product not found", 404)
    line = conn.execute(
        "SELECT quantity FROM cart_items WHERE user_id = ? AND product_id = ?",
        (user["id"], product_id),
    ).fetchone()
    total_qty = quantity + (line["quantity"] if line else 0)
    if product["stock"] == 0:
        conn.close()
        return err("out of stock", 400)
    if total_qty > 10:
        conn.close()
        return err("quantity per product cannot exceed 10", 400)
    if total_qty > product["stock"]:
        conn.close()
        return err(f"only {product['stock']} in stock", 400)
    if line is None:
        conn.execute(
            "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)",
            (user["id"], product_id, quantity),
        )
    else:
        conn.execute(
            "UPDATE cart_items SET quantity = ? WHERE user_id = ? AND product_id = ?",
            (total_qty, user["id"], product_id),
        )
    view = {**cart_view(conn, user["id"]), "message": "added to cart"}
    conn.commit()
    conn.close()
    return jsonify(view)


@app.put("/api/cart/update")
def cart_update():
    user, error = require_login()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity")
    error = quantity_error(quantity) or product_id_error(product_id)
    if error:
        return err(error, 400)
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        return err("product not found", 404)
    line = conn.execute(
        "SELECT id FROM cart_items WHERE user_id = ? AND product_id = ?",
        (user["id"], product_id),
    ).fetchone()
    if line is None:
        conn.close()
        return err("product not in cart", 404)
    if product["stock"] == 0:
        conn.close()
        return err("out of stock", 400)
    if quantity > product["stock"]:
        conn.close()
        return err(f"only {product['stock']} in stock", 400)
    conn.execute(
        "UPDATE cart_items SET quantity = ? WHERE user_id = ? AND product_id = ?",
        (quantity, user["id"], product_id),
    )
    view = {**cart_view(conn, user["id"]), "message": "cart updated"}
    conn.commit()
    conn.close()
    return jsonify(view)


@app.delete("/api/cart/remove/<int:product_id>")
def cart_remove(product_id):
    user, error = require_login()
    if error:
        return error
    conn = get_db()
    line = conn.execute(
        "SELECT id FROM cart_items WHERE user_id = ? AND product_id = ?",
        (user["id"], product_id),
    ).fetchone()
    if line is None:
        conn.close()
        return err("product not in cart", 404)
    conn.execute("DELETE FROM cart_items WHERE user_id = ? AND product_id = ?",
                 (user["id"], product_id))
    view = {**cart_view(conn, user["id"]), "message": "product removed from cart"}
    conn.commit()
    conn.close()
    return jsonify(view)


# ---------- coupons ----------

@app.post("/api/cart/coupon")
def apply_coupon():
    user, error = require_login()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    code = str(data.get("code") or "").strip().upper()
    if not code:
        return err("code is required", 400)
    conn = get_db()
    coupon = conn.execute("SELECT * FROM coupons WHERE code = ?", (code,)).fetchone()
    if coupon is None:
        conn.close()
        return err("invalid coupon", 404)
    _, subtotal, _ = load_cart(conn, user["id"])
    reason = coupon_reject_reason(coupon, subtotal)
    if reason is not None:
        conn.close()
        return err(reason, 400)
    conn.execute(
        "INSERT INTO applied_coupons (user_id, code, drop_message) VALUES (?, ?, NULL)"
        " ON CONFLICT(user_id) DO UPDATE SET code = excluded.code, drop_message = NULL",
        (user["id"], code),
    )
    view = {**cart_view(conn, user["id"]), "message": "coupon applied"}
    conn.commit()
    conn.close()
    return jsonify(view)


@app.delete("/api/cart/coupon")
def remove_coupon():
    user, error = require_login()
    if error:
        return error
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM applied_coupons WHERE user_id = ?", (user["id"],)
    ).fetchone()
    if row is None:
        conn.close()
        return err("no coupon applied", 404)
    conn.execute("DELETE FROM applied_coupons WHERE user_id = ?", (user["id"],))
    view = {**cart_view(conn, user["id"]), "message": "coupon removed"}
    conn.commit()
    conn.close()
    return jsonify(view)


# ---------- checkout ----------

def check_expiry(expiry):
    if not EXPIRY_RE.match(expiry):
        return "expiry must be in MM/YY format"
    month = int(expiry[:2])
    year = 2000 + int(expiry[3:])
    if not 1 <= month <= 12:
        return "expiry month must be 01-12"
    today = datetime.date.today()
    if year < today.year or (year == today.year and month < today.month):
        return "card expired"
    return None


def fetch_order(conn, order_id):
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        return None
    result = dict(order)
    result["items"] = [
        dict(r) for r in conn.execute(
            "SELECT product_id, product_name, price, quantity FROM order_items"
            " WHERE order_id = ? ORDER BY product_id",
            (order_id,),
        ).fetchall()
    ]
    return result


@app.post("/api/checkout")
def checkout():
    user, error = require_login()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    shipping = str(data.get("shipping_address") or "").strip()
    name_on_card = str(data.get("name_on_card") or "").strip()
    card = str(data.get("card_number") or "").strip().replace(" ", "")
    expiry = str(data.get("expiry") or "").strip()
    cvv = str(data.get("cvv") or "").strip()

    conn = get_db()
    items, subtotal, rows = load_cart(conn, user["id"])
    if not items:
        conn.close()
        return err("cart is empty", 400)
    if not 10 <= len(shipping) <= 200:
        conn.close()
        return err("shipping_address must be 10 to 200 characters", 400)
    if not 2 <= len(name_on_card) <= 50:
        conn.close()
        return err("name_on_card must be 2 to 50 characters", 400)
    if not CARD_RE.match(card):
        conn.close()
        return err("card number must be exactly 16 digits", 400)
    expiry_error = check_expiry(expiry)
    if expiry_error:
        conn.close()
        return err(expiry_error, 400)
    if not CVV_RE.match(cvv):
        conn.close()
        return err("cvv must be exactly 3 digits", 400)

    for row in rows:
        if row["stock"] < row["quantity"]:
            conn.close()
            return err(f'insufficient stock for "{row["name"]}"', 400)

    if card == DECLINED_CARD:
        conn.close()
        return err("payment declined", 402)

    # mock payment success: create order, snapshot items, reduce stock, clear cart+coupon
    coupon, discount, _ = evaluate_coupon(conn, user["id"], subtotal)
    total = round(subtotal - discount, 2)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    cursor = conn.execute(
        "INSERT INTO orders (user_id, subtotal, discount, total, coupon_code,"
        " shipping_address, card_last4, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user["id"], subtotal, discount, total,
         coupon["code"] if coupon else None, shipping, card[-4:], "Placed", now),
    )
    order_id = cursor.lastrowid
    for item in items:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, price, quantity)"
            " VALUES (?, ?, ?, ?, ?)",
            (order_id, item["product_id"], item["name"], item["price"], item["quantity"]),
        )
        conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?",
                     (item["quantity"], item["product_id"]))
    conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user["id"],))
    conn.execute("DELETE FROM applied_coupons WHERE user_id = ?", (user["id"],))
    conn.commit()
    order = fetch_order(conn, order_id)
    conn.close()
    return jsonify(order), 201


# ---------- orders ----------

@app.get("/api/orders")
def list_orders():
    user, error = require_login()
    if error:
        return error
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user["id"],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    user, error = require_login()
    if error:
        return error
    conn = get_db()
    order = fetch_order(conn, order_id)
    conn.close()
    if order is None or order["user_id"] != user["id"]:
        return err("order not found", 404)
    return jsonify(order)


@app.put("/api/orders/<int:order_id>/status")
def update_order_status(order_id):
    user, error = require_login()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    status = str(data.get("status") or "").strip()
    if status not in ORDER_STATUSES:
        return err("status must be one of " + ", ".join(ORDER_STATUSES), 400)
    conn = get_db()
    row = conn.execute(
        "SELECT user_id FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if row is None or row["user_id"] != user["id"]:
        conn.close()
        return err("order not found", 404)
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    order = fetch_order(conn, order_id)
    conn.close()
    return jsonify(order)


# ---------- pages ----------

@app.get("/")
def index():
    return redirect("/products")


@app.get("/login")
def login_page():
    return render_template("login.html")


@app.get("/register")
def register_page():
    return render_template("register.html")


@app.get("/products")
def products_page():
    return render_template("products.html")


@app.get("/products/<int:product_id>")
def product_detail_page(product_id):
    return render_template("product_detail.html")


@app.get("/cart")
def cart_page():
    return render_template("cart.html")


@app.get("/checkout")
def checkout_page():
    return render_template("checkout.html")


@app.get("/orders")
def orders_page():
    return render_template("orders.html")


@app.get("/orders/<int:order_id>")
def order_detail_page(order_id):
    return render_template("order_detail.html")


@app.get("/profile")
def profile_page():
    return render_template("profile.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
