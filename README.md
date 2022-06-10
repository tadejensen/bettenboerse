# Bettenbörse

## Instructions
```
cp settings.py.settings settings.py
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
pip install flask_migrate pytest
gunicorn -b 127.0.0.1:8081 app:app
```
