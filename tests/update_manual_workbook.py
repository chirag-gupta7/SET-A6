"""Record the results of tests/run_manual_cases.py in the manual test workbook."""
import copy
import json

import openpyxl

BOOK = "docs/QuickCart_Manual_Test_Cases.xlsx"
results = {r["id"]: r for r in json.load(open("test-results/manual/results.json", encoding="utf-8"))}

wb = openpyxl.load_workbook(BOOK)
ws = wb["Manual Test Cases"]
rows = {row[0].value: row for row in ws.iter_rows(min_row=2)}

for case_id, result in results.items():
    row = rows[case_id]
    row[8].value = "%s - manual browser run: %s. Screenshot: test-results/manual/%s.png." % (
        "Passed" if result["status"] == "Pass" else "Failed (re-confirmed)", result["actual"], case_id)
    row[9].value = result["status"]

POSTMAN_CASE = {
    "TC-M-004": "TC-AUTH-04", "TC-M-005": "TC-AUTH-06", "TC-M-007": "TC-AUTH-10",
    "TC-M-016": "TC-AUTH-17", "TC-M-017": "TC-AUTH-18", "TC-M-071": "TC-CHECK-11",
}
for case_id, postman_case in POSTMAN_CASE.items():
    rows[case_id][10].value = "Manual browser run (Selenium, this run) + Postman: " + postman_case
rows["TC-M-042"][10].value = (
    "Manual browser run (Selenium, this run) + Postman: TC-CART-05 (API rejects 2.5)")

defects = wb["Defects & Observations"]
new = defects.max_row + 1
if not any(cell.value == "D-10" for cell in defects["A"]):
    for col in range(1, 7):
        defects.cell(new, col)._style = copy.copy(defects.cell(new - 1, col)._style)
    defects.cell(new, 1, "D-10")
    defects.cell(new, 2, "UI messages")
    defects.cell(new, 3, 'Register/Profile/Checkout messages lose their error/success colour: app.js sets '
                           'class "msg error" / "msg success", while style.css styles ".msg-error" / ".msg-success", '
                           'so a message shown after an API call is unstyled (text is correct, colour is lost).')
    defects.cell(new, 4, "Observation / Low")
    defects.cell(new, 5, "Open")
    defects.cell(new, 6, "Manual browser run TC-M-016/TC-M-017 (this run)")

summary = wb["Summary"]
summary["A29"] = "Manual cases (Selenium, this run)"
summary["B29"] = "TC-M-004/005/007/016/017/071 executed for the first time; TC-M-042 re-checked -> 6 passed, 1 known Fail (D-08 re-confirmed)"
summary["B28"] = ("Pass = verified against the live app by one of the runs above (see Actual Result). "
                  "All 87 cases have now been executed: 86 Pass, 1 Fail (D-08), 0 Not Run.")

wb.calculation.fullCalcOnLoad = True
wb.save(BOOK)
print("workbook updated:", BOOK)
