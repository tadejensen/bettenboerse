# Bettenbörse

## Installation
```bash
cp settings.py.settings settings.py
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
gunicorn -b 127.0.0.1:8081 app:app
```

# Signal
DBUS interface is used: https://github.com/AsamK/signal-cli/wiki/DBus-service
