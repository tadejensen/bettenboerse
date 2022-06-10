# Bettenbörse

## Instructions
```
cp settings.py.settings settings.py
python3 -m venv --system-site-packages venv
source venv/bin/activate
#pip install -r requirements.txt
pip install flask_sqlalchemy wtforms flask_wtf  flask_httpauth flask_migrate flask flask_qrcode pydbus pytest gunicorn
gunicorn -b 127.0.0.1:8081 app:app
```
