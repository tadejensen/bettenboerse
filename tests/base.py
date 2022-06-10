import pytest
from app import app, db

import settings

USER = "lg"
# password = USER = lg
settings.PASSWORD_HASH = 'pbkdf2:sha256:260000$uC06clbdtW17H1kl$81c187bda181e93074f0b6083b8394aac3f2053f16464ec57b316bc49798971b'

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config["WTF_CSRF_METHODS"] = []
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as client:
        yield client
