# Bettenbörse

## Instructions
```
cp settings.py.settings settings.py
python3 -m venv venv
source venv/bin/activate
gunicorn -b 127.0.0.1:8081 app:ap
```
