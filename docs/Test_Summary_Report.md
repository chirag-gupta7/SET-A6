# QuickCart — Test Summary Report

**Date:** November 2026 · **Application:** QuickCart (Flask + sqlite3 demo shop) · **Tester:** QA course student team

## 1. Scope

Testing covered the complete QuickCart demo application: the HTTP API (registration, login, profile, products CRUD/search/filters, cart, coupons, checkout, orders/status), the rendered web UI (products list/detail, cart, checkout, orders, profile), and the required manual test-analysis documentation. The app itself was treated as the system under test; the only change made to it was the D-08 fix in the product page script (see section 5).

## 2. Approach and techniques

- **Equivalence partitioning (EP)** and **boundary value analysis (BVA)** were applied to every input with a documented rule: quantity (1–10, stock-capped), coupon minimum orders (SAVE10 500, FLAT100 1000), card number (16 digits), expiry (MM/YY, not in the past), CVV (3 digits), shipping address (10–200), names (2–50), registration fields, product price/stock. The full analysis is the "BVA_EP Analysis" sheet in `docs/QuickCart_Manual_Test_Cases.xlsx`.
- **Functional** flows (register → login → add to cart → coupon → checkout → order tracking) were scripted end to end.
- **Negative** tests: invalid emails/credentials, wrong quantities, unknown ids, expired/unknown coupons, declined card, invalid order status, cross-user access.
- Manual cases that could not be automated through normal user input (product CRUD price/stock rules, unknown product/order ids, stock race precondition) were verified at API level and are marked accordingly.

## 3. Tools

Python 3.13 `urllib` API suite (224 assertions), Postman + Newman 6.2.3 (164 requests / 355 assertions), Selenium 4.35 + pytest (17 UI tests, headless-capable), Playwright quick browser check (32 one-off UI checks used to verify the earlier manual mapping), Selenium browser run for the final manual cases (`tests/run_manual_cases.py`), openpyxl for the workbook.

## 4. Results by module (manual suite, 87 cases)

| Module | Cases | Pass | Fail | Not Run |
|---|---|---|---|---|
| Registration/Login/Profile | 18 | 18 | 0 | 0 |
| Product Catalog/Search/Filters | 13 | 13 | 0 | 0 |
| Cart | 15 | 15 | 0 | 0 |
| Coupon/Discount | 11 | 11 | 0 | 0 |
| Checkout/Payment | 22 | 22 | 0 | 0 |
| Order Tracking/History | 8 | 8 | 0 | 0 |
| **Total** | **87** | **87** | **0** | **0** |

Explain manners:

- **Pass** — all 87 cases were actually executed against the live app and recorded in the "Actual Result" column: the Newman run (0 failed of 355 assertions), the Selenium run (17/17), the earlier quick browser check (32/32), and the final manual browser run that executed the six previously deferred cases (TC-M-004/005/007/016/017/071). The precise run backing each row is in its "Automated By" cell.
- **Fail** — none. TC-M-042 (the only failure in the previous run) now passes: the product page sends the raw number instead of `parseInt`, so `2.5` reaches the API and is rejected with the normal error; regression test `TC_UI_17` covers it. Defect **D-08** is fixed.
- **Not Run** — none: the six cases previously deferred were executed in the final manual browser run and passed.

Final run artifacts are in `test-results/` (CLI output, Newman JSON report, Selenium HTML/JUnit reports, manual-case screenshots and results.json).

Earlier-step automated runs (and this step's Newman + Selenium runs on both a fresh and a dirty database) all passed: API suite 224/224 assertions, Postman 164 requests / 355 assertions / 0 failed (two runs), Selenium 16/16 tests (before the TC_UI_17 regression test was added).

## 5. Defects and observations (from the workbook sheet)

| ID | Area | Finding | Severity | Status |
|---|---|---|---|---|
| D-01 | Login | Empty login shows the generic "invalid email or password" (no specific hint) | Observation / Low | Accepted |
| D-02 | Orders | Status validation happens before ownership check (400 vs 404 on foreign order) | Observation / Low | Accepted |
| D-03 | Search | SQL LIKE wildcards `%` and `_` are not escaped | Observation / Low | Open |
| D-04 | Checkout | No stock locking for simultaneous purchases | Observation / Low | Accepted (demo) |
| D-05 | Products | No admin role; any logged-in user edits all products | Observation / Low | Accepted (demo) |
| D-06 | Deployment | Dev server + fixed secret key | Observation / Low | Accepted |
| D-07 | Coupons | No per-user coupon usage limits | Observation / Low | Accepted |
| D-08 | Cart | UI truncated non-integer quantity (2.5 → 2); API rejects it. **Fixed:** the page now sends the raw number, so the API's rejection is shown | Low | Fixed (TC_UI_17) |
| D-09 | Cart | Cart lines of deleted products disappear silently | Observation / Low | Accepted (demo) |
| D-10 | UI messages | Messages shown after API calls lose their red/green colour (JS sets `msg error`, CSS styles `.msg-error`) | Observation / Low | Open |

## 6. Conclusion

All verification conditions defined for the demo behave as designed: all 87 manual cases pass on the live app (87 Pass, 0 Fail, 0 Not Run), and the UI-layer quantity defect (D-08) that was open in the previous run is now fixed and covered by automated regression test `TC_UI_17`. One low-severity styling observation remains open (D-10: messages lose their red/green colour after an API call), alongside the accepted demo limitations. The product is fit for the course submission purpose; the two tracked Open items (D-03 wildcard search, D-10 message colour) are small, realistic fixes for a follow-up exercise.
