#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, flash, url_for, session, request
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

from flask_migrate import Migrate
from werkzeug.security import check_password_hash
from forms import SleepingPlaceForm, ReservationForm, DeleteSleepingPlace, MenschForm, DeleteMensch
from datetime import datetime, timedelta
import uuid
from flask_qrcode import QRcode

import settings

from models import ReservationState

app = Flask(__name__)
app.config['SECRET_KEY'] = settings.FLASK_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = settings.DB_LOCATION
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

QRcode(app)
auth = HTTPBasicAuth()

db = SQLAlchemy()

migrate = Migrate(app, db, compare_type=True, render_as_batch=True)


class SleepingPlace(db.Model):
    __tablename__ = 'sleeping_places'

    uuid = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(100))
    pronoun = db.Column(db.String(100))
    telephone = db.Column(db.String(100))
    address = db.Column(db.String())
    keys = db.Column(db.String())
    rules = db.Column(db.String())
    sleeping_places_basic = db.Column(db.Integer())
    sleeping_places_luxury = db.Column(db.Integer())
    date_from_june = db.Column(db.Date())
    date_to_june = db.Column(db.Date())
    latitude = db.Column(db.String())
    longitude = db.Column(db.String())
    lg_comment = db.Column(db.String())


class Mensch(db.Model):
    __tablename__ = 'menschen'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    telephone = db.Column(db.String())


class Reservation(db.Model):
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    sleeping_place = db.Column(db.String(100), db.ForeignKey(
        'sleeping_places.uuid'))
    date = db.Column(db.Date())
    #__table_args__ = (UniqueConstraint('sleeping_place', 'date', name='uniq_reservation_per_day'),)
    #state = db.Column(db.Enum(ReservationState))


class ReservationMensch(db.Model):
    __tablename__ = 'reservations_mensch'
    mensch = db.Column(db.Integer, db.ForeignKey('menschen.id'), primary_key=True)
    reservation = db.Column(db.Integer, db.ForeignKey('reservations.id'))


# this needs to be placed here!
db.init_app(app)
db.create_all(app=app)


@auth.verify_password
def verify_password(username, password):
    if username == settings.USER and \
            check_password_hash(settings.PASSWORD_HASH, password):
        session['logged_in'] = True
        return username


@app.route('/', methods=['GET', 'POST'])
def index():
    form = SleepingPlaceForm()

    if form.validate_on_submit():

        # try:     form = UserDetails(request.POST, obj=user)
        new_sp = SleepingPlace(uuid=str(uuid.uuid4()),
                               name=form.data['name'],
                               pronoun=form.data['pronoun'],
                               telephone=form.data['telephone'],
                               address=form.data['address'],
                               keys=form.data['keys'],
                               rules=form.data['rules'],
                               sleeping_places_basic=form.data['sleeping_places_basic'],
                               sleeping_places_luxury=form.data['sleeping_places_luxury'],
                               date_from_june=form.data['date_from_june'],
                               date_to_june=form.data['date_to_june'])

        db.session.add(new_sp)
        db.session.commit()
        flash("Danke, wir haben deinen Schlafplatz aufgenommen. Vielen Dank für deine Unterstützung!", "success")
        return redirect(url_for('index'))

    return render_template(
        'index.html',
        form=form,
    )


@app.route('/unterkunft/<uuid>/')
def show_sleeping_place(uuid):
    sleeping_place = SleepingPlace.query.filter_by(uuid=uuid).first()
    if not sleeping_place:
        flash("Diese Unterkunft existiert nicht.", "danger")
        return redirect(url_for('index'))

    reservations = {}
    start = sleeping_place.date_from_june
    delta = timedelta(days=1)

    to = sleeping_place.date_to_june if sleeping_place.date_to_june else settings.end_date

    if sleeping_place.date_from_june:
        while start < to:
            reservations[start] = {}
            start += delta

    res = Reservation.query.filter_by(sleeping_place=uuid).all()
    for r in res:
        if r.date not in reservations:
            print("ERROR: Schlafplatz außerhalb der Zeit in Berlin angegeben")
            continue
        staying_people = ReservationMensch.query.filter_by(reservation=r.id).all()
        print(staying_people)
        staying_people_ids = [m.mensch for m in staying_people]
        names = Mensch.query.filter(Mensch.id.in_(staying_people_ids)).all()
        names = ", ".join([x.name for x in names])

        reservations[r.date] = {'used_beds': len(staying_people), 'names': names}

    return render_template(
        'sleeping_place_show.html',
        sleeping_place=sleeping_place,
        base_url=settings.BASE_URL,
        reservations=reservations,
    )


@app.route('/unterkunft/<uuid>/reservation/<date>/edit', methods=['GET', 'POST'])
@auth.login_required
def edit_reservation(uuid, date):
    sp = SleepingPlace.query.filter_by(uuid=uuid).first()
    if not sp:
        flash("Diese Unterkunft existiert nicht.", "danger")
        return redirect(url_for('index'))
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

        return redirect(url_for('show_sleeping_place',
                                uuid=uuid,
                                _anchor=f"reservierung-{date.strftime('%d%m')}"))


@app.route('/unterkunft/<uuid>/edit', methods=['GET', 'POST'])
@auth.login_required
def edit_sleeping_place(uuid):
    sp = SleepingPlace.query.filter_by(uuid=uuid).first()
    if not sp:
        flash("Diese Unterkunft existiert nicht.", "danger")
        return redirect(url_for('index'))

    form = SleepingPlaceForm()
    if form.validate_on_submit():
        sp.name = form.data['name']
        sp.pronoun = form.data['pronoun']
        sp.telephone = form.data['telephone']
        sp.address = form.data['address']
        sp.keys = form.data['keys']
        sp.rules = form.data['rules']
        sp.sleeping_places_basic = int(form.data['sleeping_places_basic'],)
        sp.sleeping_places_luxury = int(form.data['sleeping_places_luxury'])
        sp.latitude = form.data['latitude']
        sp.longitude = form.data['longitude']
        sp.lg_comment = form.data['lg_comment']

        date_from_june = form.data['date_from_june'] if form.data['date_from_june'] else None
        sp.date_from_june = date_from_june
        date_to_june = form.data['date_to_june'] if form.data['date_to_june'] else None
        sp.date_to_june = date_to_june

        db.session.commit()
        flash("Die Änderungen wurden gespeichert", "success")
        return redirect(url_for('show_sleeping_place', uuid=uuid))

    if not form.errors:
        form = SleepingPlaceForm(name=sp.name,
                                 pronoun=sp.pronoun,
                                 telephone=sp.telephone,
                                 address=sp.address,
                                 keys=sp.keys,
                                 rules=sp.rules,
                                 sleeping_places_basic=sp.sleeping_places_basic,
                                 sleeping_places_luxury=sp.sleeping_places_luxury,
                                 date_from_june=sp.date_from_june,
                                 date_to_june=sp.date_to_june,
                                 latitude=sp.latitude,
                                 longitude=sp.longitude,
                                 lg_comment=sp.lg_comment)

    return render_template(
        'sleeping_place_edit.html',
        form=form,
    )


@app.route('/unterkunft/<uuid>/delete', methods=['GET', 'POST'])
@auth.login_required
def delete_sleeping_place(uuid):
    sp = SleepingPlace.query.filter_by(uuid=uuid).first()
    if not sp:
        flash("Diese Unterkunft existiert nicht.", "danger")
        return redirect(url_for('index'))

    form = DeleteSleepingPlace()
    if form.validate_on_submit():
        db.session.delete(sp)
        db.session.commit()
        flash("Die Unterkunft wurde gelöscht", "success")
        return redirect(url_for('list_sleeping_places'))

    return render_template(
        'sleeping_place_delete.html',
        form=form,
        sp=sp,
    )


@app.route('/unterkünfte')
@auth.login_required
def list_sleeping_places():
    sleeping_places = SleepingPlace.query

    return render_template(
        'sleeping_place_list.html',
        sleeping_places=sleeping_places,
    )


@app.route('/menschen')
@auth.login_required
def list_menschen():
    menschen = Mensch.query

    return render_template(
        'menschen_list.html',
        menschen=menschen,
    )


@app.route('/mensch/<id>/edit', methods=['GET', 'POST'])
@auth.login_required
def edit_mensch(id):
    mensch = Mensch.query.filter_by(id=id).first()
    if not mensch:
        flash("Dieser Mensch existiert nicht.", "danger")
        return redirect(url_for('list_menschen'))

    form = MenschForm()
    if form.validate_on_submit():
        mensch.name = form.data['name']
        mensch.telephone = form.data['telephone']
        db.session.commit()
        flash("Die Änderungen wurden gespeichert", "success")
        return redirect(url_for('list_menschen'))

    if not form.errors:
        form = MenschForm(name=mensch.name,
                          telephone=mensch.telephone)

    return render_template(
        'mensch_edit.html',
        form=form
    )


@app.route('/mensch/create', methods=['GET', 'POST'])
@auth.login_required
def create_mensch():
    form = MenschForm()
    if form.validate_on_submit():
        mensch = Mensch()
        mensch.name = form.data['name']
        mensch.telephone = form.data['telephone']
        db.session.add(mensch)
        db.session.commit()
        flash("Der Mensch wurde gespeichert", "success")
        return redirect(url_for('list_menschen'))

    form = MenschForm()
    return render_template(
        'mensch_create.html',
        form=form
    )


@app.route('/mensch/<id>/delete', methods=['GET', 'POST'])
@auth.login_required
def delete_mensch(id):
    mensch = Mensch.query.filter_by(id=id).first()
    if not mensch:
        flash("Diese Mensch existiert nicht.", "danger")
        return redirect(url_for('list_menschen'))

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


@app.route('/login')
@auth.login_required
def login():
    return redirect(url_for('list_sleeping_places'))


@app.route('/test', methods=['GET', 'POST'])
def test():
    return render_template('test.html')


@app.route('/karte')
@auth.login_required
def show_map():
    date = request.args.get("date")
    if date:
        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return "Datum im falschen Format. TT.MM.YYYY", 400
        sps = SleepingPlace.query.filter(SleepingPlace.date_from_june <= date).filter(SleepingPlace.date_to_june > date).all()
    else:
        sps = SleepingPlace.query.all()
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
    #sps = SleepingPlace.query.filter_by(date_from_june=None).all()
    sps = SleepingPlace.query.filter_by().all()
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



if __name__ == '__main__':
    app.run(debug=True)
    #app.run(host="0.0.0.0", port=22000, debug=True)
