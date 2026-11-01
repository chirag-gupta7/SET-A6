"""QuickCart end-to-end UI tests: login, adding to the cart, verifying order totals.

Every test starts with a fresh browser (see the `driver` fixture), logs in as the
seeded demo user when needed, and empties the cart first so the suite can be
re-run on a database that already contains data. Prices are never hardcoded -
they are read from the UI and the expected values are computed in Python.
"""

from decimal import Decimal, ROUND_HALF_UP

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from conftest import (
    BASE_URL,
    CABLE, T_SHIRT,
    login, ensure_clean_cart, wait_cart_ready, cart_row, cart_totals,
    add_from_list, add_from_detail, apply_coupon, fill_checkout_form,
    order_items_map, shown, money, cart_count, all_product_cards,
    wait_orders_page, orders_count, product_card,
)

WAIT_ERROR = shown  # a short alias to keep error assertions readable


def go_products(driver, wait):
    """Open the product list and wait until all cards are rendered."""
    driver.get(BASE_URL + "/products")
    all_product_cards(driver, wait)


# ============================================================ LOGIN =============

def test_TC_UI_01_login_valid(driver, wait):
    """1: valid login -> lands on /products, navbar greets 'Hi, Test User'."""
    driver.get(BASE_URL + "/login")
    shown(wait, (By.ID, "login-email")).send_keys("test@quickcart.com")
    driver.find_element(By.ID, "login-password").send_keys("Test@123")
    driver.find_element(By.ID, "login-submit").click()
    wait.until(EC.url_contains("/products"))
    user = shown(wait, (By.ID, "nav-user"))
    assert user.text == "Hi, Test User"
    assert shown(wait, (By.ID, "nav-cart")).is_displayed()


def test_TC_UI_02_login_wrong_password(driver, wait):
    """2: wrong password -> stays on /login, error message is shown."""
    driver.get(BASE_URL + "/login")
    shown(wait, (By.ID, "login-email")).send_keys("test@quickcart.com")
    driver.find_element(By.ID, "login-password").send_keys("WrongPassword1")
    driver.find_element(By.ID, "login-submit").click()
    error = wait.until(lambda d: d.find_element(By.ID, "login-error")
                       if d.find_element(By.ID, "login-error").is_displayed()
                       and d.find_element(By.ID, "login-error").text else False)
    assert "login" in driver.current_url
    assert error.text == "invalid email or password"


def test_TC_UI_03_login_empty_fields(driver, wait):
    """3: empty email AND password -> an error message is displayed."""
    driver.get(BASE_URL + "/login")
    shown(wait, (By.ID, "login-email"))  # page ready
    driver.find_element(By.ID, "login-submit").click()
    error = wait.until(lambda d: d.find_element(By.ID, "login-error")
                       if d.find_element(By.ID, "login-error").is_displayed()
                       and d.find_element(By.ID, "login-error").text else False)
    assert "login" in driver.current_url
    assert error.text.strip() != ""  # whatever message the app produces


def test_TC_UI_04_logout(driver, wait):
    """4: logout -> Login link visible again, greeting hidden."""
    login(driver, wait)
    shown(wait, (By.ID, "nav-logout")).click()
    wait.until(EC.url_contains("/login"))
    assert shown(wait, (By.ID, "nav-login")).is_displayed()
    wait.until(lambda d: not d.find_element(By.ID, "nav-user").is_displayed())


# ============================================================= CART =============

def test_TC_UI_05_add_one_item(driver, wait):
    """5: add one item -> cart-count 1; the cart row shows qty 1 and line total == price."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    go_products(driver, wait)
    price = add_from_list(driver, wait, CABLE)
    driver.get(BASE_URL + "/cart")
    wait_cart_ready(driver, wait)
    row = cart_row(driver, wait, CABLE)
    assert int(row.find_element(By.CSS_SELECTOR, ".cart-qty").get_attribute("value")) == 1
    assert money(row.find_element(By.CSS_SELECTOR, ".line-total").text) == price
    assert cart_count(driver) == 1


def test_TC_UI_06_add_same_item_twice(driver, wait):
    """6: adding the same product again -> one row, qty 2, line total == 2 x price."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    go_products(driver, wait)
    price = add_from_list(driver, wait, CABLE)
    add_from_list(driver, wait, CABLE)  # quantity accumulates on the same row
    driver.get(BASE_URL + "/cart")
    wait_cart_ready(driver, wait)
    rows = driver.find_elements(By.CSS_SELECTOR, ".cart-row")
    assert len(rows) == 1
    row = cart_row(driver, wait, CABLE)
    assert int(row.find_element(By.CSS_SELECTOR, ".cart-qty").get_attribute("value")) == 2
    assert money(row.find_element(By.CSS_SELECTOR, ".line-total").text) == price * 2


def test_TC_UI_07_add_two_different_items(driver, wait):
    """7: two different products -> two rows, subtotal == sum of the line totals."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    go_products(driver, wait)
    add_from_list(driver, wait, CABLE)
    add_from_list(driver, wait, T_SHIRT)
    driver.get(BASE_URL + "/cart")
    wait_cart_ready(driver, wait)
    rows = driver.find_elements(By.CSS_SELECTOR, ".cart-row")
    assert len(rows) == 2
    line_sum = sum(money(r.find_element(By.CSS_SELECTOR, ".line-total").text) for r in rows)
    _, _, _ = cart_totals(driver)
    subtotal = money(driver.find_element(By.ID, "cart-subtotal").text)
    assert subtotal == line_sum


def test_TC_UI_08_update_quantity_to_3(driver, wait):
    """8: changing a row's quantity to 3 recalculates line total and subtotal."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    go_products(driver, wait)
    price = add_from_list(driver, wait, CABLE)
    driver.get(BASE_URL + "/cart")
    wait_cart_ready(driver, wait)
    row = cart_row(driver, wait, CABLE)
    row.find_element(By.CSS_SELECTOR, ".cart-qty").clear()
    row.find_element(By.CSS_SELECTOR, ".cart-qty").send_keys("3")
    row.find_element(By.CSS_SELECTOR, ".update-btn").click()
    wait.until(lambda d: money(cart_row(d, wait, CABLE)
              .find_element(By.CSS_SELECTOR, ".line-total").text) == price * 3)
    assert money(driver.find_element(By.ID, "cart-subtotal").text) == price * 3


def test_TC_UI_09_remove_item(driver, wait):
    """9: removing the only item -> 'cart empty' banner and cart-count 0."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    go_products(driver, wait)
    add_from_list(driver, wait, CABLE)
    driver.get(BASE_URL + "/cart")
    wait_cart_ready(driver, wait)
    cart_row(driver, wait, CABLE).find_element(By.CSS_SELECTOR, ".remove-btn").click()
    assert shown(wait, (By.ID, "cart-empty")).is_displayed()
    wait.until(lambda d: cart_count(d) == 0)


def test_TC_UI_10_add_quantity_above_max(driver, wait):
    """10: qty 11 on the product page -> error in page-message, nothing added."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    go_products(driver, wait)
    product_card(driver, wait, CABLE).find_element(By.CSS_SELECTOR, ".product-name").click()
    wait.until(lambda d: d.find_element(By.ID, "product-name").text == CABLE)
    before = cart_count(driver)
    inp = shown(wait, (By.ID, "qty-input"))
    inp.clear()
    inp.send_keys("11")
    driver.find_element(By.ID, "add-to-cart-btn").click()
    msg = WAIT_ERROR(wait, (By.ID, "page-message"))
    assert msg.text == "quantity must be an integer between 1 and 10"
    assert cart_count(driver) == before  # nothing was added


def test_TC_UI_11_add_while_logged_out(driver, wait):
    """11: guests clicking 'Add to Cart' are redirected to /login."""
    go_products(driver, wait)  # fresh browser -> not logged in
    product_card(driver, wait, CABLE).find_element(By.CSS_SELECTOR, ".add-to-cart-btn").click()
    wait.until(EC.url_contains("/login"))
    assert "/login" in driver.current_url


# ====================================================== COUPON / TOTALS =========

def test_TC_UI_12_coupon_welcome20(driver, wait):
    """12: WELCOME20 -> discount == 20% of subtotal (2 decimals), total adjusts."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    go_products(driver, wait)
    add_from_list(driver, wait, CABLE)
    driver.get(BASE_URL + "/cart")
    wait_cart_ready(driver, wait)
    subtotal, _, _ = cart_totals(driver)
    apply_coupon(driver, wait, "WELCOME20")
    expected = (subtotal * Decimal("0.2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    wait.until(lambda d: money(d.find_element(By.ID, "cart-discount").text) == expected)
    assert money(driver.find_element(By.ID, "cart-discount").text) == expected
    assert money(driver.find_element(By.ID, "cart-total").text) == subtotal - expected


def test_TC_UI_13_coupon_invalid(driver, wait):
    """13: an unknown coupon code -> error message, totals unchanged."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    go_products(driver, wait)
    add_from_list(driver, wait, CABLE)
    driver.get(BASE_URL + "/cart")
    wait_cart_ready(driver, wait)
    old_subtotal, _, old_total = cart_totals(driver)
    apply_coupon(driver, wait, "BOGUS123")
    msg = WAIT_ERROR(wait, (By.ID, "coupon-message"))
    assert msg.text == "invalid coupon"
    assert money(driver.find_element(By.ID, "cart-subtotal").text) == old_subtotal
    assert money(driver.find_element(By.ID, "cart-total").text) == old_total


# ============================================================= ORDER ============

CARD_VALID = "4111 1111 1111 1111"       # accepted by the mock payment
CARD_DECLINED = "4000000000000002"       # the app always declines this one
CARD_TOO_SHORT = "411111111111111"       # only 15 digits


def test_TC_UI_14_full_order_flow(driver, wait):
    """14: login -> 2 items -> WELCOME20 -> checkout -> order page matches the cart."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    go_products(driver, wait)
    price_cable = add_from_list(driver, wait, CABLE)          # qty 1
    price_shirt = add_from_detail(driver, wait, T_SHIRT, 2)   # qty 2

    driver.get(BASE_URL + "/cart")
    wait_cart_ready(driver, wait)
    apply_coupon(driver, wait, "WELCOME20")
    wait.until(lambda d: money(d.find_element(By.ID, "cart-discount").text) != 0)
    subtotal, discount, total = cart_totals(driver)

    driver.find_element(By.ID, "checkout-btn").click()
    wait.until(EC.url_contains("/checkout"))
    wait.until(lambda d: d.find_element(By.ID, "checkout-total").text.startswith("₹"))
    fill_checkout_form(driver, wait, CARD_VALID)
    driver.find_element(By.ID, "place-order-btn").click()

    wait.until(EC.url_matches(r"/orders/\d+"))
    order_id = wait.until(lambda d: d.current_url.split("/orders/")[1].split("?")[0])
    assert "placed=1" in driver.current_url
    banner = shown(wait, (By.ID, "order-success"))
    assert "successfully" in banner.text

    assert money(driver.find_element(By.ID, "order-subtotal").text) == subtotal
    assert money(driver.find_element(By.ID, "order-discount").text) == discount
    assert money(driver.find_element(By.ID, "order-total").text) == total
    assert order_items_map(driver, wait, 2) == {
        CABLE: (price_cable, 1),
        T_SHIRT: (price_shirt, 2),
    }
    assert driver.find_element(By.ID, "order-card").text == "**** **** **** 1111"
    assert driver.find_element(By.ID, "order-status").text == "Placed"

    driver.get(BASE_URL + "/orders")
    wait_orders_page(driver, wait)
    row = wait.until(lambda d: d.find_element(
        By.CSS_SELECTOR, '#orders-body .order-row[data-order-id="%s"]' % order_id))
    assert row.find_element(By.CSS_SELECTOR, ".order-id").text == order_id
    assert money(row.find_element(By.CSS_SELECTOR, ".order-total").text) == total

    driver.get(BASE_URL + "/cart")
    assert shown(wait, (By.ID, "cart-empty")).is_displayed()
    wait.until(lambda d: cart_count(d) == 0)


def test_TC_UI_15_declined_card(driver, wait):
    """15: the always-declined test card -> error shown, cart keeps its items."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    go_products(driver, wait)
    add_from_list(driver, wait, CABLE)
    driver.get(BASE_URL + "/checkout")
    wait.until(lambda d: d.find_element(By.ID, "checkout-total").text.startswith("₹"))
    fill_checkout_form(driver, wait, CARD_DECLINED)
    driver.find_element(By.ID, "place-order-btn").click()
    msg = WAIT_ERROR(wait, (By.ID, "checkout-error"))
    assert msg.text == "payment declined"
    assert "/orders/" not in driver.current_url  # still on the checkout page
    driver.get(BASE_URL + "/cart")
    wait_cart_ready(driver, wait)
    assert len(driver.find_elements(By.CSS_SELECTOR, ".cart-row")) == 1


def test_TC_UI_16_invalid_card_number(driver, wait):
    """16: a 15-digit card number -> error shown and no order is created."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    driver.get(BASE_URL + "/orders")
    wait_orders_page(driver, wait)
    orders_before = orders_count(driver)
    go_products(driver, wait)
    add_from_list(driver, wait, CABLE)
    driver.get(BASE_URL + "/checkout")
    wait.until(lambda d: d.find_element(By.ID, "checkout-total").text.startswith("₹"))
    fill_checkout_form(driver, wait, CARD_TOO_SHORT)
    driver.find_element(By.ID, "place-order-btn").click()
    msg = WAIT_ERROR(wait, (By.ID, "checkout-error"))
    assert msg.text == "card number must be exactly 16 digits"
    assert "/orders/" not in driver.current_url
    driver.get(BASE_URL + "/orders")
    wait_orders_page(driver, wait)
    assert orders_count(driver) == orders_before  # no order was created


def test_TC_UI_17_non_integer_quantity(driver, wait):
    """17: qty 2.5 on the product page -> API rejection message, cart unchanged (regression for D-08)."""
    login(driver, wait)
    ensure_clean_cart(driver, wait)
    go_products(driver, wait)
    product_card(driver, wait, CABLE).find_element(By.CSS_SELECTOR, ".product-name").click()
    wait.until(lambda d: d.find_element(By.ID, "product-name").text == CABLE)
    before = cart_count(driver)
    inp = shown(wait, (By.ID, "qty-input"))
    inp.clear()
    inp.send_keys("2.5")
    driver.find_element(By.ID, "add-to-cart-btn").click()
    msg = WAIT_ERROR(wait, (By.ID, "page-message"))
    assert msg.text == "quantity must be an integer between 1 and 10"
    assert cart_count(driver) == before  # nothing was added
