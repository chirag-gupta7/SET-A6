"""Shared fixtures and helpers for the QuickCart UI test suite.

Assumptions every test relies on:
- The QuickCart app is already running (BASE_URL, default http://127.0.0.1:5000;
  override with the BASE_URL environment variable).
- Chrome runs visibly so the demo can be watched; set HEADLESS=1 for headless mode.
- The seeded demo user is test@quickcart.com / Test@123 (display name "Test User").
- Only explicit waits (WebDriverWait + expected_conditions) are used, never time.sleep,
  because product cards, cart rows and the auth state are rendered by JavaScript.
"""

import os
import urllib.request
from decimal import Decimal, ROUND_HALF_UP

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
HEADLESS = os.environ.get("HEADLESS", "") == "1"

EMAIL = "test@quickcart.com"
PASSWORD = "Test@123"
NAME = "Test User"

# Seed-catalog products used by the tests, chosen because both have plenty of stock:
CABLE = "USB-C Charging Cable"   # seed stock 40
T_SHIRT = "Cotton T-Shirt"       # seed stock 50


@pytest.fixture(scope="session", autouse=True)
def app_must_be_running():
    """Check once per run that the app is reachable; fail every test with a clear message."""
    url = BASE_URL + "/api/health"
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            if resp.status != 200:
                raise RuntimeError("HTTP %d" % resp.status)
    except Exception as exc:
        pytest.fail(
            "QuickCart is not reachable at %s (%s).\n"
            "Start the app first: cd ..\\quickcart, then python app.py" % (url, exc),
            pytrace=False,
        )


@pytest.fixture
def driver():
    """A fresh browser per test, so tests never share cookies or page state."""
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1600,1000")
    drv = webdriver.Chrome(options=options)  # Selenium Manager provides the driver binary
    if not HEADLESS:
        drv.maximize_window()
    yield drv
    drv.quit()


@pytest.fixture
def wait(driver):
    """One explicit-wait object (10s) per test, shared by all helpers."""
    return WebDriverWait(driver, 10)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Save ./screenshots/<test_name>.png whenever a test fails."""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        drv = item.funcargs.get("driver")
        if drv is not None:
            folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
            os.makedirs(folder, exist_ok=True)
            drv.save_screenshot(os.path.join(folder, item.name + ".png"))


# ---------- small helpers used by many tests ----------

def money(text):
    """'₹499.99' -> Decimal('499.99'), so money maths is done with Decimals."""
    return Decimal(text.replace("₹", "").replace(",", "").strip())


def rupee(value):
    """Format a Decimal the way the UI does: '₹' + value.toFixed(2)."""
    return "₹" + str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def shown(wait, locator):
    """Wait until the element exists AND is visible, then return it."""
    return wait.until(EC.visibility_of_element_located(locator))


def cart_count(d):
    """The number inside the navbar's 'Cart (N)' (updates after every cart action)."""
    return int(d.find_element(By.ID, "cart-count").text)


def find_card(d, name):
    """False until the product card with `name` is rendered (DOM keeps re-rendering)."""
    try:
        for card in d.find_elements(By.CSS_SELECTOR, ".product-card"):
            if card.find_element(By.CSS_SELECTOR, ".product-name").text == name:
                return card
    except Exception:  # element went stale mid-render - the wait will simply retry
        pass
    return False


def product_card(driver, wait, name):
    """Wait for the product card with the given name on /products and return it."""
    return wait.until(lambda d: find_card(d, name))


def all_product_cards(driver, wait):
    """Wait until /products has finished rendering, return every .product-card."""
    return wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".product-card"))


def login(driver, wait):
    """Log in as the seeded demo user; ends on /products with the navbar filled."""
    driver.get(BASE_URL + "/login")
    shown(wait, (By.ID, "login-email")).send_keys(EMAIL)
    driver.find_element(By.ID, "login-password").send_keys(PASSWORD)
    driver.find_element(By.ID, "login-submit").click()
    wait.until(EC.url_contains("/products"))
    wait.until(lambda d: d.find_element(By.ID, "nav-user").text == "Hi, " + NAME)


def ensure_clean_cart(driver, wait):
    """Empty the cart and drop any leftover coupon, so runs on a dirty DB are safe.

    Leftovers exist because the database is not reset between test runs.
    Removes every cart row one by one (the rows are re-rendered after each removal,
    so the list is re-read on every loop turn).
    """
    driver.get(BASE_URL + "/cart")
    wait_cart_ready(driver, wait)
    driver.find_element(By.ID, "remove-coupon-btn").click()
    wait.until(lambda d: d.find_element(By.ID, "coupon-message").text != "")
    while True:
        rows = driver.find_elements(By.CSS_SELECTOR, ".cart-row")
        if not rows:
            break
        before = len(rows)
        rows[0].find_element(By.CSS_SELECTOR, ".remove-btn").click()
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".cart-row")) < before
                   or d.find_element(By.ID, "cart-empty").is_displayed())
    shown(wait, (By.ID, "cart-empty"))
    wait.until(lambda d: cart_count(d) == 0)


def wait_cart_ready(driver, wait):
    """The cart body is rendered by JS: rows appear, or the empty banner shows."""
    wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".cart-row")
               or d.find_element(By.ID, "cart-empty").is_displayed())


def cart_row(driver, wait, name):
    """Wait for the .cart-row whose .cart-name matches; rows are re-created by JS
    after every action, so never cache this element across an action."""
    def finder(d):
        try:
            for row in d.find_elements(By.CSS_SELECTOR, ".cart-row"):
                if row.find_element(By.CSS_SELECTOR, ".cart-name").text == name:
                    return row
        except Exception:  # stale element while re-rendering - retry
            pass
        return False
    return wait.until(finder)


def cart_totals(d):
    """Read subtotal, discount, total from the cart page as Decimals."""
    return (money(d.find_element(By.ID, "cart-subtotal").text),
            money(d.find_element(By.ID, "cart-discount").text),
            money(d.find_element(By.ID, "cart-total").text))


def add_from_list(driver, wait, name):
    """Click 'Add to Cart' on the product's card in the list; returns its UI price."""
    card = product_card(driver, wait, name)
    price = money(card.find_element(By.CSS_SELECTOR, ".product-price").text)
    before = cart_count(driver)
    card.find_element(By.CSS_SELECTOR, ".add-to-cart-btn").click()
    wait.until(lambda d: cart_count(d) == before + 1)
    return price


def add_from_detail(driver, wait, name, qty):
    """Open the product detail page, set the quantity, add; returns its UI price."""
    product_card(driver, wait, name).find_element(By.CSS_SELECTOR, ".product-name").click()
    wait.until(lambda d: d.find_element(By.ID, "product-name").text == name)
    price = money(driver.find_element(By.ID, "product-price").text)
    before = cart_count(driver)
    shown(wait, (By.ID, "qty-input")).clear()
    driver.find_element(By.ID, "qty-input").send_keys(str(qty))
    driver.find_element(By.ID, "add-to-cart-btn").click()
    wait.until(lambda d: cart_count(d) == before + qty)
    return price


def apply_coupon(driver, wait, code):
    """Type a coupon code into the cart page and click Apply."""
    box = shown(wait, (By.ID, "coupon-input"))
    box.clear()
    box.send_keys(code)
    driver.find_element(By.ID, "apply-coupon-btn").click()


def fill_checkout_form(driver, wait, card_number):
    """Fill the checkout form; only the card number differs between the E2E tests."""
    shown(wait, (By.ID, "shipping-address")).send_keys("42 Test Lane, Springfield, 123456")
    driver.find_element(By.ID, "card-name").send_keys(NAME)
    driver.find_element(By.ID, "card-number").send_keys(card_number)
    driver.find_element(By.ID, "card-expiry").send_keys("12/30")
    driver.find_element(By.ID, "card-cvv").send_keys("123")


def order_items_map(driver, wait, expected_count):
    """Wait for `expected_count` .order-item rows, then map name -> (price, qty)."""
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#order-items .order-item"))
               == expected_count)
    items = {}
    for row in driver.find_elements(By.CSS_SELECTOR, "#order-items .order-item"):
        items[row.find_element(By.CSS_SELECTOR, ".item-name").text] = (
            money(row.find_element(By.CSS_SELECTOR, ".item-price").text),
            int(row.find_element(By.CSS_SELECTOR, ".item-qty").text),
        )
    return items


def wait_orders_page(driver, wait):
    """The orders table is rendered by JS: rows appear, or the 'no orders' banner shows."""
    wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, "#orders-body .order-row")
               or d.find_element(By.ID, "orders-empty").is_displayed())


def orders_count(driver):
    return len(driver.find_elements(By.CSS_SELECTOR, "#orders-body .order-row"))
