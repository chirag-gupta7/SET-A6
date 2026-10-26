# QuickCart Postman collection
Import both JSON files into Postman (File > Import), pick the "QuickCart env" environment, and run the collection (start the API first: `cd ..\quickcart` then `python app.py`). Login runs on session cookies; a logged-out state is produced by the API's own POST /api/logout.

Newman:
```
npm install -g newman
newman run QuickCart.postman_collection.json -e QuickCart.postman_environment.json
```
Re-runnable on the same database - run it twice in a row, no reset needed (random user emails + own test products per run).
