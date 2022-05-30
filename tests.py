#!/usr/bin/env python3
import pytest

from app import app, db, SleepingPlace

from settings import USER
import settings
settings.PASSWORD_HASH = 'pbkdf2:sha256:260000$uC06clbdtW17H1kl$81c187bda181e93074f0b6083b8394aac3f2053f16464ec57b316bc49798971b'


@pytest.fixture
def client():
    #db_fd, flaskr.app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config["WTF_CSRF_METHODS"] = []
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as client:
        #with app.app_context():
        #    app.init_db()
        yield client

    #os.close(db_fd)
    #os.unlink(flaskr.app.config['DATABASE'])


def test_index(client):
    resp = client.get('/')
    assert resp.status_code == 200


def test_loginclient(client):
    resp = client.get('/unterkünfte')
    assert resp.status_code == 401


def test_auth_needed(client):
    resp = client.get('/unterkünfte')
    assert resp.status_code == 401


def test_login(client):
    resp = client.get('/login', auth=(USER, USER))
    assert resp.status_code == 302


def test_list_unterkuenfte(client):
    resp = client.get('/unterkünfte', auth=(USER, USER))
    assert "Übersicht Schlafplätze" in resp.text
    for sp in SleepingPlace.query.all():
        assert sp.uuid in resp.text
        assert sp.name in resp.text
        assert sp.address in resp.text


def test_unterkunft_details(client):
    resp = client.get("/")
    for sp in SleepingPlace.query.all():
        resp = client.get(f"/unterkunft/{sp.uuid}/", auth=(USER, USER))
        assert resp.status_code == 200
        assert "Übersicht Unterkunft" in resp.text
        assert sp.uuid in resp.text
        assert sp.name in resp.text
        assert sp.address in resp.text


def test_add_unterkunft(client):
    data = {'name': 'testname',
            'pronoun': 'pronomen',
            'telephone': 'tele',
            'address': 'address',
            'keys': 'keys',
            'rules': 'rules',
            'sleeping_places_basic': 0,
            'sleeping_places_luxury': 0,
            'date_from_june': '2022-06-10',
            'date_to_june': '2022-06-15',
            }
    resp = client.post("/", data=data, follow_redirects=False)
    assert resp.status_code == 302
    for sp in SleepingPlace.query.filter_by(name="testname"):
        print(f"Deleting {sp}")
        db.session.delete(sp)
    db.session.commit()
