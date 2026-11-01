# How to Run QuickCart

## Prerequisites
- Python 3.13+
- (Optional) Node.js + Newman for the Postman collection
- (Optional) Chrome for Selenium UI tests

## 1. Install dependencies
```powershell
pip install -r quickcart\requirements.txt
pip install -r selenium_tests\requirements.txt
```

## 2. Run the app
```powershell
cd quickcart
python app.py
```
Open http://127.0.0.1:5000

Reset to a clean demo state: stop the server, delete `quickcart\quickcart.db`, start again.

## 3. Demo login
- Email: test@quickcart.com
- Password: Test@123

## 4. Run the API tests (Python)
Start the app on a fresh DB first, then:
```powershell
python tests\test_api.py
```

## 5. Run the Postman collection (Newman)
```powershell
npm install -g newman
cd postman
newman run QuickCart.postman_collection.json -e QuickCart.postman_environment.json
```

## 6. Run the Selenium UI tests
Start the app first, then:
```powershell
cd selenium_tests
python -m pytest test_quickcart_ui.py -v
# headless:
$env:HEADLESS="1"; python -m pytest test_quickcart_ui.py -v
```

## 7. Run the manual cases that need a browser
Start the app first, then from the project root:
```powershell
python tests\run_manual_cases.py
```
It executes the manual cases that need real UI input (TC-M-004/005/007/016/017/071), re-checks the known TC-M-042 defect, and writes screenshots + `results.json` to `test-results\manual\`.