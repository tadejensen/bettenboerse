#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, flash, url_for, session
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import check_password_hash
from forms import SleepingPlaceForm, ReservationForm, DeleteSleepingPlace
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


class Reservation(db.Model):
    __tablename__ = 'reservations'

    sleeping_place = db.Column(db.String(100), db.ForeignKey(
        'sleeping_places.uuid'), primary_key=True)
    date = db.Column(db.Date(), primary_key=True)
    reservation = db.Column(db.String())
    state = db.Column(db.Enum(ReservationState))
    free_beds = db.Column(db.Integer())


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
            #reservations[start.date()] = {}
            reservations[start] = {}
            start += delta

    res = Reservation.query.filter_by(sleeping_place=uuid).all()
    for r in res:
        if r.date not in reservations:
            print("ERROR: Schlafplatz außerhalb der Zeit in Berlin angegeben")
            continue
        reservations[r.date] = r

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

    reservation = Reservation.query.filter_by(
        sleeping_place=uuid, date=date).first()
    form = ReservationForm()
    if form.validate_on_submit():
        if reservation:
            reservation.reservation = form.data['reservation']
            reservation.state = form.data['state']
            reservation.free_beds = form.data['free_beds']
        else:
            res = Reservation(sleeping_place=uuid,
                              date=date,
                              reservation=form.data['reservation'],
                              state=form.data['state'],
                              free_beds=form.data['free_beds'])
            db.session.add(res)
        db.session.commit()
        flash("Reservierung gespeichert", "success")
        return redirect(url_for('show_sleeping_place',
                                uuid=uuid,
                                _anchor=f"reservierung-{date.strftime('%d%m')}"))

    # TODO: find a smarter logic here
    if form.errors:
        pass
    elif reservation:
        form = ReservationForm(reservation=reservation.reservation,
                               state=reservation.state.name,
                               free_beds=reservation.free_beds)
    else:
        form = ReservationForm(date=date)

    return render_template(
        'reservation_edit.html',
        form=form,
        uuid=uuid,
        date=date,
        sleeping_place=sp,
    )


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
        'list.html',
        sleeping_places=sleeping_places,
    )


@app.route('/login')
@auth.login_required
def login():
    return redirect(url_for('list_sleeping_places'))


@app.route('/karte')
@auth.login_required
def show_map():
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
                           sps=complete_sps)


@app.route('/test')
def test():
    #sps = SleepingPlace.query.filter_by(date_from_june=None).all()
    sps = SleepingPlace.query.filter_by().all()
    for sp in sps:
        if sp.date_from_june:
            if sp.date_to_june:
                print(f"{sp.sleeping_places_luxury + sp.sleeping_places_basic:>4} Betten {sp.date_from_june} {sp.date_to_june} {(sp.date_to_june - sp.date_from_june).days} Tage")
            else:
                print(f"{sp.sleeping_places_luxury + sp.sleeping_places_basic:>4} {sp.date_from_june} {sp.date_to_june} - kein End-Datum angegeben")
        else:
            print(f"MAI: {sp.sleeping_places_luxury + sp.sleeping_places_basic:>4} {sp.date_from_may} {sp.date_to_may} - kein End-Datum angegeben")
    delta = timedelta(days=1)

    start = settings.start_date
    end = settings.end_date
    beds = {}

    while start < end:
        free_beds = 0
        places = []
        for sp in sps:
            if not sp.date_from_june:
                #print(f"{sp} has no from date ({start})")
                continue
            if not sp.date_to_june:
                sp.date_to_june = end
            if start >= sp.date_from_june and start <= sp.date_to_june:
                free_beds += sp.sleeping_places_luxury
                free_beds += sp.sleeping_places_basic
                places.append(sp.name)
        #beds[start] = {'free_beds': free_beds, 'sp': places}
        beds[start] = free_beds
        start += delta
    for day, beds in beds.items():
        print(f"{day}: {beds}")
    return ""


   #for sp in sps:
   #    print(sp.name, sp.telephone, "\n", f"https://bettenboerse.letztegeneration.de/unterkunft/{sp.uuid}/")


if __name__ == '__main__':
    app.run(debug=True)
    #app.run(host="0.0.0.0", port=22000, debug=True)
