"""QuickCart database helper: connection, schema init, seed data."""
import os
import sqlite3

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quickcart.db")

SEED_PRODUCTS = [
    # (name, description, category, price, stock, image_url)
    # one item stock 0 (Table Lamp), one item stock 3 (Study Chair), rest 10-50
    ("USB-C Charging Cable", "Braided 1m USB-C charging cable", "Electronics", 99, 40,
     "http://example.com/img/usb-c-cable.jpg"),
    ("Wireless Mouse", "Silent click 2.4GHz wireless mouse", "Electronics", 499, 25,
     "http://example.com/img/wireless-mouse.jpg"),
    ("Bluetooth Headphones", "Over-ear headphones with mic", "Electronics", 1499, 30,
     "http://example.com/img/bluetooth-headphones.jpg"),
    ("Cotton T-Shirt", "Plain round neck cotton t-shirt", "Clothing", 299, 50,
     "http://example.com/img/cotton-tshirt.jpg"),
    ("Denim Jeans", "Slim fit stretchable denim jeans", "Clothing", 1299, 20,
     "http://example.com/img/denim-jeans.jpg"),
    ("Running Shoes", "Lightweight mesh running shoes", "Clothing", 2499, 15,
     "http://example.com/img/running-shoes.jpg"),
    ("Python Crash Course", "Beginner friendly python programming book", "Books", 199, 35,
     "http://example.com/img/python-crash-course.jpg"),
    ("Data Science Handbook", "Reference handbook for data science", "Books", 599, 12,
     "http://example.com/img/data-science-handbook.jpg"),
    ("Short Story Collection", "Anthology of short stories", "Books", 349, 45,
     "http://example.com/img/short-story-collection.jpg"),
    ("Table Lamp", "Adjustable reading lamp for study table", "Home", 899, 0,
     "http://example.com/img/table-lamp.jpg"),
    ("Ceramic Mug Set", "Set of 6 ceramic mugs", "Home", 249, 28,
     "http://example.com/img/ceramic-mug-set.jpg"),
    ("Study Chair", "Ergonomic chair with lumbar support", "Home", 5000, 3,
     "http://example.com/img/study-chair.jpg"),
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            phone TEXT,
            address TEXT
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            image_url TEXT
        );
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            UNIQUE (user_id, product_id)
        );
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            value REAL NOT NULL,
            min_order REAL NOT NULL,
            expires_on TEXT
        );
        CREATE TABLE IF NOT EXISTS applied_coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            code TEXT NOT NULL,
            drop_message TEXT
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            discount REAL NOT NULL,
            total REAL NOT NULL,
            coupon_code TEXT,
            shipping_address TEXT NOT NULL,
            card_last4 TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL
        );
        """
    )
    # seed only when the tables are empty
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Test User", "test@quickcart.com", generate_password_hash("Test@123")),
        )
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO products (name, description, category, price, stock, image_url)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            SEED_PRODUCTS,
        )
    if conn.execute("SELECT COUNT(*) FROM coupons").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO coupons (code, type, value, min_order, expires_on) VALUES (?, ?, ?, ?, ?)",
            [
                ("SAVE10", "percent", 10, 500, None),
                ("FLAT100", "flat", 100, 1000, None),
                ("WELCOME20", "percent", 20, 0, None),
                ("OLD50", "flat", 50, 0, "2020-01-01"),
            ],
        )
    conn.commit()
    conn.close()
