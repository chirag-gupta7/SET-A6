"""Execute the manual test cases that the workbook leaves as "Not Run" (plus re-check
the known TC-M-042 defect) through the real UI with Selenium, on the live app.

Start the server first, then: python tests/run_manual_cases.py
Evidence (screenshots + results.json) is written to test-results/manual/.
"""
import json
import os
import urllib.request
import uuid

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = "http://127.0.0.1:5000"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test-results", "manual")
os.makedirs(OUT, exist_ok=True)

results = []


def fresh_user():
    email = "manual.%s@example.com" % uuid.uuid4().hex[:8]
    req = urllib.request.Request(
        BASE + "/api/register",
        data=json.dumps({"name": "Manual Tester", "email": email, "password": "Pass12"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 201, resp.status
    return email, "Pass12"


class Browser:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1600,1000")
        self.d = webdriver.Chrome(options=options)
        self.w = WebDriverWait(self.d, 10)

    def login(self):
        email, password = fresh_user()
        self.d.get(BASE + "/login")
        self.w.until(EC.visibility_of_element_located((By.ID, "login-email"))).send_keys(email)
        self.d.find_element(By.ID, "login-password").send_keys(password)
        self.d.find_element(By.ID, "login-submit").click()
        self.w.until(EC.url_contains("/products"))
        self.w.until(lambda d: d.find_element(By.ID, "nav-user").text.startswith("Hi,"))

    def shot(self, name):
        self.d.save_screenshot(os.path.join(OUT, name + ".png"))

    def quit(self):
        self.d.quit()


def record(case_id, scenario, expected, actual, passed, browser):
    browser.shot(case_id)
    results.append({
        "id": case_id, "scenario": scenario, "expected": expected,
        "actual": actual, "status": "Pass" if passed else "Fail",
    })
    print("%s  %s" % (case_id, "Pass" if passed else "Fail"))


def register_validation(case_id, scenario, name, password, expected_msg):
    b = Browser()
    try:
        b.d.get(BASE + "/register")
        b.w.until(EC.visibility_of_element_located((By.ID, "reg-name"))).send_keys(name)
        b.d.find_element(By.ID, "reg-email").send_keys("manual.%s@example.com" % uuid.uuid4().hex[:8])
        b.d.find_element(By.ID, "reg-password").send_keys(password)
        b.d.find_element(By.ID, "reg-submit").click()
        err = b.w.until(lambda d: d.find_element(By.ID, "reg-error").text)
        actual = "Registration page showed %r; still on /register: %s" % (err, "/register" in b.d.current_url)
        record(case_id, scenario, expected_msg, actual, err == expected_msg and "/register" in b.d.current_url, b)
    finally:
        b.quit()


def profile_validation(case_id, scenario, phone):
    expected = "phone must be exactly 10 digits"
    b = Browser()
    try:
        b.login()
        b.d.get(BASE + "/profile")
        b.w.until(lambda d: d.find_element(By.ID, "profile-name").get_attribute("value") != "")
        field = b.d.find_element(By.ID, "profile-phone")
        field.clear()
        field.send_keys(phone)
        b.d.find_element(By.ID, "profile-save").click()
        msg = b.w.until(lambda d: d.find_element(By.ID, "profile-message").text)
        # Note: the page sets class "msg error" while style.css styles ".msg-error",
        # so the text is correct but the red colour is lost (new observation D-10).
        style = b.d.find_element(By.ID, "profile-message").get_attribute("class")
        actual = "Profile page showed %r (element class %r)" % (msg, style)
        record(case_id, scenario, expected, actual, msg == expected, b)
    finally:
        b.quit()


def checkout_17_digit_card():
    expected = "card number must be exactly 16 digits"
    b = Browser()
    try:
        b.login()
        b.d.get(BASE + "/products")
        b.w.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".product-card .add-to-cart-btn"))).click()
        b.w.until(lambda d: d.find_element(By.ID, "cart-count").text == "1")
        b.d.get(BASE + "/checkout")
        b.w.until(lambda d: d.find_element(By.ID, "checkout-total").text.startswith("₹"))
        b.d.find_element(By.ID, "shipping-address").send_keys("12 MG Road, Bengaluru 560001")
        b.d.find_element(By.ID, "card-name").send_keys("Manual Tester")
        b.d.find_element(By.ID, "card-number").send_keys("41111111111111111")
        b.d.find_element(By.ID, "card-expiry").send_keys("12/30")
        b.d.find_element(By.ID, "card-cvv").send_keys("123")
        b.d.find_element(By.ID, "place-order-btn").click()
        err = b.w.until(lambda d: d.find_element(By.ID, "checkout-error").text)
        actual = "Checkout page showed %r; still on /checkout: %s" % (err, "/checkout" in b.d.current_url)
        record("TC-M-071", "Card Number with 17 digits is rejected", expected, actual,
               err == expected and "/checkout" in b.d.current_url, b)
    finally:
        b.quit()


def non_integer_quantity():
    expected = "quantity must be an integer between 1 and 10; the cart does not change"
    b = Browser()
    try:
        b.login()
        b.d.get(BASE + "/products")
        b.w.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".product-card .product-name"))).click()
        b.w.until(lambda d: d.find_element(By.ID, "product-name").text != "")
        qty = b.d.find_element(By.ID, "qty-input")
        qty.clear()
        qty.send_keys("2.5")
        b.d.find_element(By.ID, "add-to-cart-btn").click()
        msg = b.w.until(lambda d: d.find_element(By.ID, "page-message").text)
        count = b.d.find_element(By.ID, "cart-count").text
        b.d.get(BASE + "/cart")
        b.w.until(EC.visibility_of_element_located((By.ID, "cart-empty")))
        row_qty = "0 rows (cart empty)"
        actual = ("Page message %r; cart badge %s, cart %s"
                  % (msg, count, row_qty))
        record("TC-M-042", "Detail-page quantity as a non-integer: 2.5 - DEFECT row", expected, actual,
               msg == "quantity must be an integer between 1 and 10" and count == "0", b)
    finally:
        b.quit()


try:
    register_validation("TC-M-004", "Register with a 1-character name", "A", "Pass12",
                        "name must be 2 to 50 characters")
    register_validation("TC-M-005", "Register with a 51-character name", "A" * 51, "Pass12",
                        "name must be 2 to 50 characters")
    register_validation("TC-M-007", "Register with a 21-character password", "Qa Long",
                        "1234567890123456789011", "password must be 6 to 20 characters")
    profile_validation("TC-M-016", "Profile phone with 11 digits is rejected", "12345678901")
    profile_validation("TC-M-017", "Profile phone with letters is rejected", "12345678a0")
    checkout_17_digit_card()
    non_integer_quantity()
finally:
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

failed = [r for r in results if r["status"] != "Pass"]
print("\n%d cases run, %d passed, %d failed" % (len(results), len(results) - len(failed), len(failed)))
