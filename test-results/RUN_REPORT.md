# QuickCart — Test Run Report

**Run date:** 2026-11-01 (final run, after the D-08 fix) · **App:** QuickCart Flask demo (`quickcart/app.py`) on `http://127.0.0.1:5000`
**Environment:** Windows 11, Python 3.13.3, Flask 3.0.0, Selenium 4.35.0, pytest 8.4.2, Node 22.23.4, Newman 6.2.3, Chrome (headless)

The app was started on a fresh database (`quickcart/quickcart.db` deleted first). All suites below were run against that live server in this order.

## Summary

| # | Suite | Result | Evidence |
|---|---|---|---|
| 1 | API suite (`tests/test_api.py`) | **224 passed, 0 failed** | `api-test-output.txt` |
| 2 | Page-route / element-id checks (`tests/check_ids.py`) | **135 passed, 0 failed** | `page-id-check-output.txt` |
| 3 | Postman collection (Newman) | **164 requests, 355 assertions, 0 failed** | `newman-output.txt`, `newman-report.json` |
| 4 | Selenium UI suite (`selenium_tests/`) | **17 passed, 0 failed** (headless) | `selenium-output.txt`, `selenium-report.html`, `selenium-junit.xml` |
| 5 | Manual cases needing real UI input (`tests/run_manual_cases.py`) | **7 passed, 0 failed** | `manual/results.json`, `manual/TC-M-*.png` |

## Fix verified in this run: D-08 (TC-M-042)

The product detail page used `parseInt(qty)`, which silently turned `2.5` into `2` before the request, so the API's correct rejection never appeared. The page now uses `Number(qty)` (and the cart page's Update button does the same), so `2.5` reaches the API and the normal validation message is shown; nothing is added to the cart.

Regression coverage: new Selenium test `TC_UI_17_non_integer_quantity` (17th UI test) plus the manual case TC-M-042 — both pass on the live app.

## Manual cases executed in this run

| Case | Scenario | Result | What the UI actually showed |
|---|---|---|---|
| TC-M-004 | Register, 1-character name | Pass | `name must be 2 to 50 characters`, stayed on /register |
| TC-M-005 | Register, 51-character name | Pass | `name must be 2 to 50 characters`, stayed on /register |
| TC-M-007 | Register, 21-character password | Pass | `password must be 6 to 20 characters`, stayed on /register |
| TC-M-016 | Profile phone, 11 digits | Pass | `phone must be exactly 10 digits` |
| TC-M-017 | Profile phone with a letter | Pass | `phone must be exactly 10 digits` |
| TC-M-071 | Checkout card number, 17 digits | Pass | `card number must be exactly 16 digits`, stayed on /checkout |
| TC-M-042 | Product page quantity `2.5` | **Pass** | `quantity must be an integer between 1 and 10`; cart badge unchanged |

These were the six workbook cases marked "Not Run" plus the previously failing TC-M-042. The workbook `docs/QuickCart_Manual_Test_Cases.xlsx` now totals **87 Pass / 0 Fail / 0 Not Run**, and D-08 is marked Fixed.

## Open observation (not fixed)

**D-10 (Observation / Low, Open)** — messages shown after an API call lose their red/green colour: `app.js` sets `class="msg error"` / `"msg success"` while `style.css` styles `.msg-error` / `.msg-success`. Text is correct; only the colour is lost.

## How to reproduce

```powershell
# fresh DB, app running
cd quickcart; python app.py

# from the project root
python tests\test_api.py
python tests\check_ids.py
cd postman; newman run QuickCart.postman_collection.json -e QuickCart.postman_environment.json
cd ..\selenium_tests; $env:HEADLESS="1"; python -m pytest test_quickcart_ui.py -v
cd ..; python tests\run_manual_cases.py
```

The manual runner needs the server up and writes its own screenshots + `results.json`; `tests/update_manual_workbook.py` copies those results into the workbook.
