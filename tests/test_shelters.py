import pytest
from .base import client, USER, db
from bettenboerse.app import Shelter, Mensch, app, settings
import uuid
from datetime import date, datetime


@pytest.fixture(autouse=True)
def my_fixture():
    with app.app_context():
        assert Shelter.query.filter(Shelter.name.like("test_unterkunft%")).all() == []
        assert Mensch.query.filter(Mensch.name.like("alerta%")).all() == []
        yield
        assert Shelter.query.filter(Shelter.name.like("test_unterkunft%")).all() == []
        assert Mensch.query.filter(Mensch.name.like("alerta%")).all() == []


def test_add_valid_shelter(client):
    name = "test_unterkunft1312"
    data = {'name': name,
            'pronoun': 'pronomen',
            'telephone': 'tele',
            'address': 'address',
            'keys': 'keys',
            'rules': 'rules',
            'beds_basic': 0,
            'beds_luxury': 0,
            'date_from_june': '2022-06-10',
            'date_to_june': '2022-06-15',
            }

    # check add view
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 200

    # add shelter
    resp = client.post("/", data=data, follow_redirects=False)
    assert resp.status_code == 302

    shelter = Shelter.query.filter_by(name=name).first()
    assert shelter

    # check list view
    resp = client.get('/unterkünfte', auth=(USER, USER))
    assert "Übersicht Unterkünfte" in resp.text
    assert shelter.uuid in resp.text
    assert shelter.name in resp.text
    assert shelter.address in resp.text

    # check detail view
    resp = client.get(f"/unterkunft/{shelter.uuid}/", auth=(USER, USER))
    assert resp.status_code == 200
    assert "Übersicht Unterkunft" in resp.text
    assert shelter.name in resp.text
    assert shelter.address in resp.text
    # assert settings.phone_shelter_support != ""
    # assert settings.phone_vor_ort_support != ""
    # assert settings.phone_ea != ""
    # assert settings.phone_logistics != ""
    # assert settings.phone_shelter_support in resp.text
    # assert settings.phone_vor_ort_support in resp.text
    # assert settings.phone_ea in resp.text
    # assert settings.phone_logistics in resp.text

    # check delete view
    resp = client.get(f"/unterkunft/{shelter.uuid}/delete", auth=(USER, USER))
    assert resp.status_code == 200

    # delete unterkunft
    data = {'submit': 'Unterkunft löschen'}
    resp = client.post(f"/unterkunft/{shelter.uuid}/delete", data=data, follow_redirects=False, auth=(USER, USER))
    assert resp.status_code == 302

    # check list view
    resp = client.get('/unterkünfte', auth=(USER, USER))
    assert name not in resp.text


def test_list_unterkuenfte(client):
    resp = client.get('/unterkünfte', auth=(USER, USER))
    assert "Übersicht Unterkünfte" in resp.text
    for shelter in Shelter.query.all():
        assert shelter.uuid in resp.text
        assert shelter.name in resp.text
        assert shelter.address in resp.text


def test_unterkunft_details_view(client):
    resp = client.get("/")
    for shelter in Shelter.query.all():
        resp = client.get(f"/unterkunft/{shelter.uuid}/", auth=(USER, USER))
        assert resp.status_code == 200
        assert "Übersicht Unterkunft" in resp.text
        assert shelter.uuid in resp.text
        assert shelter.name in resp.text
        assert shelter.address in resp.text


def test_all_unterkünfte_detail_view(client):
    resp = client.get("/")
    for shelter in Shelter.query.all():
        resp = client.get(f"/unterkunft/{shelter.uuid}/", auth=(USER, USER))
        assert resp.status_code == 200
        assert "Übersicht Unterkunft" in resp.text
        assert shelter.name in resp.text
        assert shelter.address in resp.text


def test_all_unterkünfte_detail_edit(client):
    resp = client.get("/")
    for shelter in Shelter.query.all():
        resp = client.get(f"/unterkunft/{shelter.uuid}/edit", auth=(USER, USER))
        assert resp.status_code == 200
        assert "Unterkunft editieren" in resp.text
        assert shelter.name in resp.text
        assert shelter.address in resp.text


def test_add_invalid_unterkunft_date(client):
    data = {'name': 'test_unterkunft111',
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
    assert "This field is required" in resp.text

    data['date_from_june'] = '2022-06-20'
    resp = client.post("/", data=data, follow_redirects=False)
    assert resp.status_code == 200
    assert "Das End-Datum liegt vor dem Start-Datum" in resp.text


def test_shelter_reservation(client):
    # I need this to get context to get the db context!?
    client.get('/', auth=(USER, USER))
    id = str(uuid.uuid4())
    shelter = Shelter(uuid=id,
                      name="test_unterkunft_should_not_exist",
                      pronoun="sie/her",
                      telephone="0123123123",
                      address="Aufm Acker 4",
                      keys="Türe ist immer offen",
                      rules="no rules",
                      beds_basic=1,
                      beds_luxury=0,
                      date_from_june=date(year=2022, month=6, day=20),
                      date_to_june=date(year=2022, month=6, day=22))
    db.session.add(shelter)
    db.session.commit()

    resp = client.get(f"/unterkunft/{id}/edit", auth=(USER, USER))
    assert resp.status_code == 200
    assert "Unterkunft editieren" in resp.text

    resp = client.get(f"/unterkunft/{id}/reservation/21.06.202222222/edit", auth=(USER, USER))
    assert resp.status_code == 400
    assert "Datum im falschen Format angegeben" in resp.text

    resp = client.get(f"/unterkunft/{id}/reservation/21.06.2022/edit", auth=(USER, USER))
    assert resp.status_code == 200
    assert "Reservierung ändern" in resp.text

    mensch = Mensch(name="alerta", bezugsgruppe="erste reihe", telephone="0123",
            date_from=datetime(year=2021, month=6, day=22), date_to=datetime(year=2023, month=6, day=28))
    mensch2 = Mensch(name="alerta2", bezugsgruppe="erste reihe", telephone="0483",
            date_from=datetime(year=2021, month=6, day=22), date_to=datetime(year=2023, month=6, day=28))
    db.session.add(mensch)
    db.session.add(mensch2)
    db.session.commit()
    mensch_id = mensch.id
    mensch2_id = mensch2.id

    data = {'mensch': 123123123}
    resp = client.post(f"/unterkunft/{id}/reservation/21.06.2022/edit", data=data, auth=(USER, USER), follow_redirects=False)
    assert resp.status_code == 200
    assert "Kein Mensch mit der id 123123123 zum hinzufügen gefunden" in resp.text

    data = {'mensch': [mensch_id, mensch2_id]}
    resp = client.post(f"/unterkunft/{id}/reservation/21.06.2022/edit", data=data, auth=(USER, USER), follow_redirects=False)
    assert resp.status_code == 200
    assert "Mehr Menschen ausgewählt als Betten verfügbar (2 ausgewählt, 1 verfügbar)" in resp.text

    data = {'mensch': mensch_id}
    resp = client.post(f"/unterkunft/{id}/reservation/21.06.2022/edit", data=data, auth=(USER, USER), follow_redirects=False)
    assert resp.status_code == 302

    resp = client.get(f"/unterkunft/{id}/", auth=(USER, USER), follow_redirects=False)
    assert resp.status_code == 200
    assert "alerta" in resp.text

    # first delete reservation before deletion
    data = {}
    resp = client.post(f"/unterkunft/{id}/reservation/21.06.2022/edit", data=data, auth=(USER, USER), follow_redirects=False)
    assert resp.status_code == 302

    mensch = Mensch.query.get(mensch_id)
    mensch2 = Mensch.query.get(mensch2_id)
    db.session.delete(mensch)
    db.session.delete(mensch2)
    db.session.delete(shelter)
    db.session.commit()

"""
TODOS:
- Mensch hat schon ne Unterkunft für die Nacht
"""
