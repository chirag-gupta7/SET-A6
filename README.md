# QuickCart — QA Course Test Project

QuickCart is a small online shop demo built for a QA/testing course: a Flask + sqlite3 web app (products, cart, coupons, checkout, orders, profile) with three layers of testing around it — a plain-Python API suite, a Postman/Newman collection, and a Selenium UI suite. Everything is inside this one folder and can be run locally with Python 3.13+, nothing cloud-hosted.

## Tech stack

| Layer | Tools |
|---|---|
| App | Python 3.13, Flask 3.0.0, sqlite3 (file DB `quickcart/quickcart.db`), vanilla JS frontend |
| API tests | Python standard library (`tests/test_api.py`, 224 assertions) |
| API tests (Postman) | Postman collection + environment, runnable via Newman 6.x |
| UI tests | Selenium 4.x (Selenium Manager auto-driver), pytest, pytest-html |
| Manual testing docs | `docs/QuickCart_Manual_Test_Cases.xlsx` (BVA/EP analysis + 87 manual cases) |

## Folder structure

```
A6 Project/
├── quickcart/            # the application (do not modify)
│   ├── app.py            # API + page routes
│   ├── db.py             # schema + seed data (products, coupons, demo user)
│   ├── templates/        # Jinja templates
│   ├── static/           # app.js + style.css
│   └── quickcart.db      # sqlite DB, created on first run (delete to reset)
├── tests/test_api.py     # API test suite (start the server first)
├── postman/              # Postman collection + environment + README
├── selenium_tests/       # Selenium UI suite (pytest)
├── docs/                 # Manual test cases (xlsx) + Test_Summary_Report.md
└── README.md             # this file
```

## How to run the app

```
cd quickcart
python app.py
```

Open http://127.0.0.1:5000. To reset to a clean demo state: stop the server, delete `quickcart\quickcart.db`, start again.

## Demo data

- **Demo user:** test@quickcart.com / Test@123
- **Coupons:** `WELCOME20` 20% off (min order 0) · `SAVE10` 10% off (min order 500) · `FLAT100` flat ₹100 off (min order 1000) · `OLD50` flat 50, **expired 2020-01-01** (used to test the expired class)
- **Test cards:** success `1234 5678 9012 3456` · declined `4000000000000002` (402, cart stays intact)

## How to run the tests

**API suite (Python)** — start the app on a fresh DB first, then:

```
python tests/test_api.py
```

**Postman (Newman)** — from the `postman` folder:

```
npm install -g newman
newman run QuickCart.postman_collection.json -e QuickCart.postman_environment.json
```

Re-runnable on a dirty DB (random test users + the collection creates/deletes its own test products). To use in the Postman GUI: File > Import both JSON files, pick "QuickCart env", run the collection.

**Selenium UI (pytest)** — from the `selenium_tests` folder, start the app first, then:

```
pip install -r requirements.txt
python -m pytest test_quickcart_ui.py -v            # visible Chrome
$env:HEADLESS="1"; python -m pytest test_quickcart_ui.py -v   # headless
```

Re-runnable on a dirty DB; failures save a screenshot to `selenium_tests/screenshots/`.

## Test coverage summary

| Suite | Size | Status |
|---|---|---|
| API suite (`tests/test_api.py`) | 224 assertions | all pass (fresh DB run) |
| Postman collection | 164 requests / 355 assertions | all pass (run twice: fresh DB + dirty DB) |
| Selenium UI suite | 16 tests | all pass (fresh DB + dirty DB runs) |
| Manual test cases (`docs/`) | 87 cases | 86 Pass, 1 Fail (D-08), 0 Not Run |
| Defects & observations log | 10 entries | 7 accepted observations + 3 open low items (D-03, D-08, D-10) |

## QA focus areas (mapping)

1. **Manual testing with BVA / EP analysis** — `docs/QuickCart_Manual_Test_Cases.xlsx`: equivalence-class and boundary analysis for quantity, coupon minimums, coupon validity, card number, expiry, CVV, address, names, registration fields, price/stock; 87 manual test cases mapped to the analysis rows (TC-M-001 … TC-M-087).
2. **API testing with Postman** — `postman/`: 8 folders (Setup → Auth & Profile → Products → Cart → Coupons → Checkout → Orders → Cleanup), every request has named `pm.test` assertions, covers every BVA/EP class at API level, re-runnable and self-cleaning.
3. **Selenium UI automation** — `selenium_tests/`: 16 UI flows (TC_UI_01 … 16) with explicit waits, fresh browser per test, re-runnable, headless option, failure screenshots.

## Known limitations (full list in the Defects & Observations sheet)

- Any logged-in user can manage all products (no admin role) — demo scope.
- Search does not escape SQL LIKE wildcards (`%`, `_`).
- No stock locking between simultaneous purchases; no per-user coupon usage limits.
- Dev server with a fixed secret key; not production-ready.
- UI defect found during manual testing: a non-integer quantity typed on the product page (e.g. `2.5`) is silently truncated to `2` by the page script (the API itself rejects it). See D-08 / TC-M-042.
- UI messages lose their red/green colour after an API call (JS sets `msg error`, CSS styles `.msg-error`). See D-10.
