#!/usr/bin/env python3
import pytest
from app import app, db, SleepingPlace
import settings

USER = "lg"
# password: lg
settings.PASSWORD_HASH = 'pbkdf2:sha256:260000$uC06clbdtW17H1kl$81c187bda181e93074f0b6083b8394aac3f2053f16464ec57b316bc49798971b'


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config["WTF_CSRF_METHODS"] = []
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as client:
        yield client


def test_index(client):
    resp = client.get('/')
    assert resp.status_code == 200


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


def test_unterkunft_details_view(client):
    resp = client.get("/")
    for sp in SleepingPlace.query.all():
        print(f"Testing {sp}")
        resp = client.get(f"/unterkunft/{sp.uuid}/", auth=(USER, USER))
        assert resp.status_code == 200
        assert "Übersicht Unterkunft" in resp.text
        assert sp.uuid in resp.text
        assert sp.name in resp.text
        assert sp.address in resp.text


def test_unterkunft_edit_view(client):
    resp = client.get("/")
    for sp in SleepingPlace.query.all():
        print(f"Testing {sp}")
        resp = client.get(f"/unterkunft/{sp.uuid}/edit", auth=(USER, USER))
        assert resp.status_code == 200
        assert "Unterkunft editieren" in resp.text
        assert sp.name in resp.text
        assert sp.address in resp.text


def test_add_valid_unterkunft(client):
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


def test_add_invalid_unterkunft(client):
    data = {'name': '',
            'pronoun': '',
            'telephone': '',
            'address': '',
            'keys': '',
            'rules': '',
            'sleeping_places_basic': 0,
            'sleeping_places_luxury': 0,
            'date_from_june': '',
            'date_to_june': '',
            }
    resp = client.post("/", data=data, follow_redirects=False)
    assert resp.status_code == 200
    assert "[&#39;This field is required.&#39;] (name)" in resp.text
    assert "[&#39;This field is required.&#39;] (pronoun)" in resp.text
    assert "[&#39;This field is required.&#39;] (telephone)" in resp.text
    assert "[&#39;This field is required.&#39;] (keys)" in resp.text
    assert "[&#39;This field is required.&#39;] (rules)" in resp.text
    assert "[&#39;This field is required.&#39;] (date_from_june)" in resp.text
    assert "[&#39;This field is required.&#39;] (date_to_june)" not in resp.text


def test_add_invalid_unterkunft_date(client):
    data = {'name': 'Hans',
            'pronoun': 'er',
            'telephone': '0123',
            'address': 'Haupstraße 4',
            'keys': 'Briefkasten',
            'rules': 'alles erlaubt',
            'sleeping_places_basic': 2,
            'sleeping_places_luxury': 1,
            'date_from_june': '',
            'date_to_june': '2022-06-18',
            }
    resp = client.post("/", data=data, follow_redirects=False)
    assert resp.status_code == 200
    assert "[&#39;This field is required.&#39;] (date_from_june)" in resp.text

    data['date_from_june'] = '2022-06-20'
    resp = client.post("/", data=data, follow_redirects=False)
    assert resp.status_code == 200
    assert "Das End-Datum liegt vor dem End-Datum" in resp.text


def test_map(client):
    resp = client.get('/karte', auth=(USER, USER))
    assert resp.status_code == 200
