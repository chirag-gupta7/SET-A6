# QuickCart UI tests (Selenium + pytest)

1. Start the app first: `cd ..\quickcart` then `python app.py` (leave it running).
2. Install dependencies: `pip install -r requirements.txt`
3. Run visible (good for demos): `python -m pytest test_quickcart_ui.py -v`
4. Run headless: `$env:HEADLESS="1"; python -m pytest test_quickcart_ui.py -v`  (bash: `HEADLESS=1 python -m pytest ...`)
5. Optional HTML report: add `--html=report.html --self-contained-html`

- Another server: set `BASE_URL` (default `http://127.0.0.1:5000`).
- On failure a screenshot is saved to `./screenshots/<test_name>.png`.
- The suite can be re-run on a non-fresh DB: every test gets a fresh browser and empties the cart first.
