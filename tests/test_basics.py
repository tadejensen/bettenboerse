from base import client, USER, db


def test_login(client):
    resp = client.get('/login', auth=(USER, USER))
    assert resp.status_code == 302


def test_login(client):
    resp = client.get('/login', auth=(USER, "this is wrong"))
    assert resp.status_code == 401


def test_auth(client):
    for path in ["/unterkünfte",
                 "/karte",
                 "/übersicht",
                 "/menschen",
                 "/mensch/add",
                 "/mensch/1/edit",
                 "/mensch/1/delete",
                 "/unterkünfte",
                 "/unterkunft/123/edit",
                 "/unterkunft/123/delete",
                 "/unterkunft/123/reservation/20.20/edit"]:
        resp = client.get(path)
        assert resp.status_code == 401, path


def test_map(client):
    resp = client.get('/karte', auth=(USER, USER))
    assert resp.status_code == 200


def test_map_with_date(client):
    resp = client.get('/karte?date=2022-06-17', auth=(USER, USER))
    assert resp.status_code == 200


def test_overview(client):
    resp = client.get('/übersicht', auth=(USER, USER))
    assert resp.status_code == 200
