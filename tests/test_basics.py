from .base import client, USER, db


def test_login(client):
    resp = client.get('/login', auth=(USER, USER))
    assert resp.status_code == 302


def test_login(client):
    resp = client.get('/login', auth=(USER, "this is wrong"))
    assert resp.status_code == 401


def test_no_auth_needed(client):
    for path in ["/", "/mensch/add", "/suche-schlafplatz"]:
        resp = client.get(path)
        assert resp.status_code == 200, path


def test_auth(client):
    for path in ["/unterkünfte",
                 "/karte",
                 "/übersicht",
                 "/menschen",
                 "/mensch/1/edit",
                 "/mensch/1/delete",
                 "/unterkünfte",
                 "/unterkunft/123/edit",
                 "/unterkunft/123/delete",
                 "/unterkunft/123/reservation/20.20/edit",
                 "reservierungen",
                 "hinweise"]:
        resp = client.get(path)
        assert resp.status_code == 401, path


def test_map(client):
    resp = client.get('/karte', auth=(USER, USER))
    assert resp.status_code == 200


def test_reservations(client):
    resp = client.get('/reservierungen', auth=(USER, USER))
    assert resp.status_code == 200


def test_show_warnings(client):
    resp = client.get('/hinweise', auth=(USER, USER))
    assert resp.status_code == 200


def test_map_with_date(client):
    resp = client.get('/karte?date=2022-06-17', auth=(USER, USER))
    assert resp.status_code == 200


def test_overview(client):
    resp = client.get('/übersicht', auth=(USER, USER))
    assert resp.status_code == 200
