"""Page-route checks for the QuickCart frontend.

Part 1: every page route must answer HTTP 200 and its raw HTML must contain
        every static element id listed in STATIC_IDS below (server-rendered,
        so assertable without JavaScript).
Part 2: ids/classes rendered by client-side JavaScript live in DYNAMIC below -
        documented only, NOT asserted against raw HTML.
Part 3: NAVBAR ids are asserted on every page.

Run with the server up:  python tests/check_ids.py
"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:5000"

NAV_IDS = [
    "nav-products", "nav-cart", "nav-orders", "nav-profile", "nav-login",
    "nav-register", "nav-logout", "nav-user", "cart-count",
]

STATIC_IDS = {
    "/products": [
        "search-input", "category-filter", "min-price", "max-price", "sort-select",
        "apply-filters", "clear-filters", "product-list", "no-results", "page-message",
    ],
    "/products/1": [
        "product-name", "product-price", "product-category", "product-stock",
        "product-description", "qty-input", "add-to-cart-btn", "page-message",
    ],
    "/cart": [
        "cart-items", "cart-subtotal", "cart-discount", "cart-total", "coupon-input",
        "apply-coupon-btn", "remove-coupon-btn", "coupon-message", "cart-empty",
        "checkout-btn", "page-message",
    ],
    "/checkout": [
        "shipping-address", "card-name", "card-number", "card-expiry", "card-cvv",
        "place-order-btn", "checkout-error", "checkout-subtotal", "checkout-discount",
        "checkout-total",
    ],
    "/orders": ["orders-table", "orders-empty"],
    "/orders/1": [
        "order-id", "order-status", "order-subtotal", "order-discount", "order-total",
        "order-coupon", "order-address", "order-card", "order-items", "order-success",
        "page-message", "status-select", "update-status-btn", "step-placed",
        "step-packed", "step-shipped", "step-delivered",
    ],
    "/profile": [
        "profile-name", "profile-email", "profile-phone", "profile-address",
        "profile-save", "profile-message",
    ],
}

# ids/classes that do NOT exist in raw HTML - created/filled by app.js at runtime.
DYNAMIC = {
    "/products": [
        'div.product-card (with data-product-id)',
        'a.product-name (link to /products/<id>)',
        'div.product-price',
        'div.product-stock ("In stock: N" / "Out of stock")',
        'button.add-to-cart-btn (with data-product-id)',
        'nav-user text "Hi, <name>", cart-count value, login/register links',
    ],
    "/products/<id>": [
        'values of product-name/product-price/product-category/product-stock/'
        'product-description (static ids, filled by JS)',
    ],
    "/cart": [
        'div.cart-row (with data-product-id, class cart-row)',
        'span.cart-name, span.cart-price, input.cart-qty (class)',
        'button.update-btn, button.remove-btn (classes)',
        'span.line-total',
        'checkout-btn hidden when cart empty; coupon-message text/coupon_message',
    ],
    "/checkout": [
        'summary values + place-order enables/disables when cart empty',
    ],
    "/orders": [
        'tr.order-row (with data-order-id)',
        'td.order-id, td.order-date, td.order-total, td.order-status',
        'a.view-order (link to /orders/<id>)',
    ],
    "/orders/<id>": [
        'values of all static ids above; div.order-item (class) with span.item-name, '
        'span.item-price, span.item-qty',
        'tracker highlight: matching step-* gets class "active"',
        'order-success visible when query ?placed=1',
    ],
    "navbar (all pages)": [
        'auth-only block visible when logged in; guest-only (login/register) visible when out',
    ],
}

PASS, FAIL = [], []


def fetch(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as resp:
            return resp.status, resp.read().decode(), resp.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), BASE + path


for path, ids in STATIC_IDS.items():
    status, html, _ = fetch(path)
    ok_status = (status == 200)
    (PASS if ok_status else FAIL).append((f"GET {path} -> 200", status, 200, ""))
    for el_id in NAV_IDS:
        (PASS if el_id in html else FAIL).append((f"{path} contains id {el_id}", status, "", ""))
    for el_id in ids:
        if el_id in NAV_IDS:
            continue
        (PASS if el_id in html else FAIL).append((f"{path} contains id {el_id}", status, "", ""))

# / must redirect to /products (urllib follows the redirect)
status, html, final_url = fetch("/")
root_ok = status == 200 and final_url.endswith("/products")
(PASS if root_ok else FAIL).append(("/ redirects to /products", final_url, "/products", ""))

print(f"PASS: {len(PASS)}   FAIL: {len(FAIL)}")
for label, status, expect, _ in FAIL:
    print(f"FAIL: {label}  (got={status!r}, expect={expect!r})")

print("\nDynamic ids/classes rendered by app.js (documented, not asserted):")
print(json.dumps(DYNAMIC, indent=2))
sys.exit(1 if FAIL else 0)
