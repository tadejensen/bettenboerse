#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, flash, url_for, session, request
from flask_httpauth import HTTPBasicAuth
from sqlalchemy import UniqueConstraint

from flask_migrate import Migrate
from werkzeug.security import check_password_hash
from forms import ShelterForm, ReservationForm, DeleteShelter, MenschForm, DeleteMensch
from datetime import datetime, timedelta
import uuid
from flask_qrcode import QRcode

import settings

from models import ReservationState, Shelter, Mensch#, Reservation, ReservationMensch
from models import Shelter, Reservation

app = Flask(__name__)
app.config['SECRET_KEY'] = settings.FLASK_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = settings.DB_LOCATION
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

QRcode(app)
auth = HTTPBasicAuth()

from models import db

migrate = Migrate(app, db, compare_type=True, render_as_batch=True)

db.init_app(app)
db.create_all(app=app)




@app.route('/', methods=['GET', 'POST'])
def add_shelter():
    form = ShelterForm()

    if form.validate_on_submit():
        shelter = Shelter(uuid=str(uuid.uuid4()))
        form.populate_obj(shelter)
        db.session.add(shelter)
        db.session.commit()
        flash("Danke, wir haben deinen Schlafplatz aufgenommen. Vielen Dank für deine Unterstützung!", "success")
        return redirect(url_for('add_shelter'))

    return render_template(
        'shelter_add.html',
        form=form,
    )


@app.route('/unterkunft/<uuid>/edit', methods=['GET', 'POST'])
@auth.login_required
def edit_shelter(uuid):
    shelter = Shelter.query.get_or_404(uuid, description=f"Unterkunft mit der id {uuid} wurde nicht gefunden")
    form = ShelterForm(obj=shelter)
    if form.validate_on_submit():
        form.populate_obj(shelter)
        date_from_june = form.data['date_from_june'] if form.data['date_from_june'] else None
        shelter.date_from_june = date_from_june
        date_to_june = form.data['date_to_june'] if form.data['date_to_june'] else None
        shelter.date_to_june = date_to_june
        shelter.sleeping_places_basic = int(form.data['sleeping_places_basic'])
        shelter.sleeping_places_luxury = int(form.data['sleeping_places_luxury'])
        db.session.commit()
        flash("Die Änderungen wurden gespeichert", "success")
        return redirect(url_for('show_shelter', uuid=uuid))

    return render_template(
        'shelter_edit.html',
        form=form,
    )


@app.route('/unterkunft/<uuid>/')
def show_shelter(uuid):
    shelter = Shelter.query.get_or_404(uuid, description=f"Unterkunft mit der id {uuid} wurde nicht gefunden")

    reservations = {}
    start = shelter.date_from_june
    end = shelter.date_to_june if shelter.date_to_june else settings.end_date
    delta = timedelta(days=1)

    while start < end:
        reservations_per_day = Reservation.query.filter_by(shelter=shelter).filter_by(date=start).all()
        # TODO: das geht schöner
        reservations[start] = {'used_beds': len(reservations_per_day), 'reservations': reservations_per_day}
        start += delta

    return render_template(
        'shelter_show.html',
        shelter=shelter,
        base_url=settings.BASE_URL,
        reservations=reservations,
    )


@app.route('/unterkunft/<uuid>/reservation/<date>/edit', methods=['GET', 'POST'])
@auth.login_required
def edit_reservation(uuid, date):
    sp = Shelter.query.filter_by(uuid=uuid).first()
    if not sp:
        flash("Diese Unterkunft existiert nicht.", "danger")
        return redirect(url_for('add_shelter'))
    # TODO: check if for start und end (between from and to)
    try:
        date = datetime.strptime(date, "%d.%m.%Y").date()
    except ValueError:
        return "Datum im falschen Format. TT.MM.YYYY", 400

    menschen = Mensch.query.all()
    reservation = Reservation.query.filter(Reservation.sleeping_place == uuid). \
                      filter(Reservation.date == date).first()

    already_reserved = []
    if request.method == "GET":
        if reservation:
            already_reserved = ReservationMensch.query.filter_by(reservation=reservation.id).all()
            already_reserved = [p.mensch for p in already_reserved]
        return render_template(
            'reservation_edit.html',
            uuid=uuid,
            date=date,
            menschen=menschen,
            sleeping_place=sp,
            already_reserved=already_reserved,
        )

    if request.method == "POST":
        ids_menschen_all = [m.id for m in menschen]
        ids_menschen_submitted = request.form.to_dict(flat=False).get('mensch', [])

        for id in ids_menschen_submitted:
            if int(id) not in ids_menschen_all:
                return f"Kein Mensch mit der id {id} gefunden", 400
        if not reservation:
            reservation = Reservation(sleeping_place=uuid, date=date)
            db.session.add(reservation)
        print("Deleting all reservations with reservation_id", reservation.id)
        ReservationMensch.query.filter_by(reservation=reservation.id).delete()

        for mensch_id in ids_menschen_submitted:
            print("Doing Mensch", mensch_id)
            reservationMensch = ReservationMensch(reservation=reservation.id, mensch=mensch_id)
            db.session.add(reservationMensch)
        db.session.commit()

        return redirect(url_for('show_shelter',
                                uuid=uuid,
                                _anchor=f"reservierung-{date.strftime('%d%m')}"))




@app.route('/unterkunft/<uuid>/delete', methods=['GET', 'POST'])
@auth.login_required
def delete_shelter(uuid):
    sp = Shelter.query.filter_by(uuid=uuid).first()
    if not sp:
        flash("Diese Unterkunft existiert nicht.", "danger")
        return redirect(url_for('add_shelter'))

    form = DeleteShelter()
    if form.validate_on_submit():
        db.session.delete(sp)
        db.session.commit()
        flash("Die Unterkunft wurde gelöscht", "success")
        return redirect(url_for('list_shelters'))

    return render_template(
        'sleeping_place_delete.html',
        form=form,
        sp=sp,
    )


@app.route('/unterkünfte')
@auth.login_required
def list_shelters():
    shelters = Shelter.query.all()

    return render_template(
        'shelter_list.html',
        shelters=shelters,
    )


@app.route('/menschen')
@auth.login_required
def list_menschen():
    menschen = Mensch.query

    return render_template(
        'menschen_list.html',
        menschen=menschen,
    )


@app.route('/mensch/add', methods=['GET', 'POST'])
@auth.login_required
def create_mensch():
    form = MenschForm()
    if form.validate_on_submit():
        mensch = Mensch()
        form.populate_obj(mensch)
        db.session.add(mensch)
        db.session.commit()
        flash("Der Mensch wurde gespeichert", "success")
        return redirect(url_for('list_menschen'))

    return render_template(
        'mensch_add.html',
        form=form
    )


@app.route('/mensch/<id>/edit', methods=['GET', 'POST'])
@auth.login_required
def edit_mensch(id):
    mensch = Mensch.query.get_or_404(id, description=f"Mensch mit der id {id} wurde nicht gefunden")
    form = MenschForm(obj=mensch)

    if form.validate_on_submit():
        form.populate_obj(mensch)
        db.session.commit()
        flash("Die Änderungen wurden gespeichert", "success")
        return redirect(url_for('list_menschen'))

    return render_template(
        'mensch_edit.html',
        form=form
    )


@app.route('/mensch/<id>/delete', methods=['GET', 'POST'])
@auth.login_required
def delete_mensch(id):
    mensch = Mensch.query.get_or_404(id, description=f"Mensch mit der id {id} wurde nicht gefunden")
    form = DeleteMensch()

    if form.validate_on_submit():
        db.session.delete(mensch)
        db.session.commit()
        flash("Der Mensch wurde aus dem System entfernt", "success")
        return redirect(url_for('list_menschen'))

    return render_template(
        'mensch_delete.html',
        form=form,
        mensch=mensch
    )


@app.route('/karte')
@auth.login_required
def show_map():
    date = request.args.get("date")
    if date:
        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return "Datum im falschen Format. TT.MM.YYYY", 400
        sps = Shelter.query.filter(Shelter.date_from_june <= date).filter(Shelter.date_to_june > date).all()
    else:
        sps = Shelter.query.all()
    empty_sps = []
    complete_sps = []
    for sp in sps:
        if sp.latitude and len(sp.latitude) > 0:
            complete_sps.append(sp)
        else:
            empty_sps.append(sp)
    return render_template('map.html',
                           empty_sps=empty_sps,
                           sps=complete_sps,
                           date=date)


@app.route('/übersicht')
def overview():
    #sps = Shelter.query.filter_by(date_from_june=None).all()
    sps = Shelter.query.filter_by().all()
    sps_list = []
    for sp in sps:
        if sp.date_to_june:
            sps_list.append(f"{sp.name:<50} {sp.sleeping_places_luxury + sp.sleeping_places_basic:>4} Betten   {sp.date_from_june} -> {sp.date_to_june}   {(sp.date_to_june - sp.date_from_june).days} Tage")
        else:
            sps_list.append(f"{sp.name:<50} {sp.sleeping_places_luxury + sp.sleeping_places_basic:>4} Betten   {sp.date_from_june} -> {sp.date_to_june} - kein End-Datum angegeben")
    delta = timedelta(days=1)

    start = settings.start_date
    end = settings.end_date
    beds = {}

    while start < end:
        beds_total = 0
        used_beds = 0
        places = []
        for sp in sps:
            if not sp.date_from_june:
                #print(f"{sp} has no from date ({start})")
                continue
            if not sp.date_to_june:
                sp_end = end
            else:
                sp_end = sp.date_to_june
            if start >= sp.date_from_june and start <= sp_end:
                beds_total += sp.sleeping_places_luxury
                beds_total += sp.sleeping_places_basic
                places.append(sp.name)

            reservation = Reservation.query.filter(Reservation.sleeping_place == sp.uuid). \
                              filter(Reservation.date == start).first()
            if reservation:
                used_beds += ReservationMensch.query.filter_by(reservation=reservation.id).count()

        beds[start] = {'beds_total': beds_total, 'used_beds': used_beds}
        start += delta
    for day, bed in beds.items():
        print(f"{day}: {bed}")
    print(beds)
    return render_template("übersicht.html", beds=beds, sleeping_places=sps_list)


@app.route("/shell")
def shell():
    m = Mensch.query.first()
    s = Shelter.query.first()
    r = Reservation(mensch=m, shelter=s, date=datetime(day=21, month=7, year=2022))
    db.session.add(r)
    db.session.commit()
    return "ok"


@auth.verify_password
def verify_password(username, password):
    if username == settings.USER and \
            check_password_hash(settings.PASSWORD_HASH, password):
        session['logged_in'] = True
        return username


@app.route('/login')
@auth.login_required
def login():
    return redirect(url_for('list_shelters'))


#@app.route('/test', methods=['GET', 'POST'])
#def test():
#    return render_template('test.html')


@app.errorhandler(404)
def page_not_found(description):
    return render_template("404.html", description=description), 404


if __name__ == '__main__':
    app.run(debug=True)
    #app.run(host="0.0.0.0", port=22000, debug=True)
