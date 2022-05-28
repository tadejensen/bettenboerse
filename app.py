#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, flash, url_for, session
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from forms import SleepingPlaceForm
from datetime import datetime
import uuid
from flask_qrcode import QRcode

import settings


app = Flask(__name__)
app.config['SECRET_KEY'] = settings.FLASK_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = settings.DB_LOCATION

QRcode(app)
auth = HTTPBasicAuth()

db = SQLAlchemy()


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
    date_from_may = db.Column(db.DateTime())
    date_to_may = db.Column(db.DateTime())
    date_from_june = db.Column(db.DateTime())
    date_to_june = db.Column(db.DateTime())


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
    print(session)
    form = SleepingPlaceForm()

    if form.validate_on_submit():
        new_sp = SleepingPlace(uuid=str(uuid.uuid4()),
                               name=form.data['name'],
                               pronoun=form.data['pronoun'],
                               telephone=form.data['telephone'],
                               address=form.data['address'],
                               keys=form.data['keys'],
                               rules=form.data['rules'],
                               sleeping_places_basic=form.data['sleeping_places_basic'],
                               sleeping_places_luxury=form.data['sleeping_places_luxury'],
                               date_from_may=form.data['date_from_may'],
                               date_to_may=form.data['date_to_may'],
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

    return render_template(
        'sleeping_place_show.html',
        sleeping_place=sleeping_place,
        base_url=settings.BASE_URL
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

        date_from_may = datetime.combine(form.data['date_from_may'], datetime.min.time()) if form.data['date_from_may'] else None
        sp.date_from_may = date_from_may
        date_to_may = datetime.combine(form.data['date_to_may'], datetime.min.time()) if form.data['date_to_may'] else None
        sp.date_to_may = date_to_may

        date_from_june = datetime.combine(form.data['date_from_june'], datetime.min.time()) if form.data['date_from_june'] else None
        sp.date_from_june = date_from_june
        date_to_june = datetime.combine(form.data['date_to_june'], datetime.min.time()) if form.data['date_to_june'] else None
        sp.date_to_june = date_to_june

        db.session.commit()
        flash("Die Änderungen wurden gespeichert", "success")
        return redirect(url_for('show_sleeping_place', uuid=uuid))

    form = SleepingPlaceForm(name=sp.name,
                             pronoun=sp.pronoun,
                             telephone=sp.telephone,
                             address=sp.address,
                             keys=sp.keys,
                             rules=sp.rules,
                             sleeping_places_basic=sp.sleeping_places_basic,
                             sleeping_places_luxury=sp.sleeping_places_luxury,
                             date_from_may=sp.date_from_may,
                             date_to_may=sp.date_to_may,
                             date_from_june=sp.date_from_june,
                             date_to_june=sp.date_to_june)

    return render_template(
        'sleeping_place_edit.html',
        form=form,
    )


@app.route('/unterkünfte')
@auth.login_required
def show_all_sleeping_places():
    sleeping_places = SleepingPlace.query

    return render_template(
        'list.html',
        sleeping_places=sleeping_places
    )


@app.route('/login')
@auth.login_required
def login():
    return redirect(url_for('show_all_sleeping_places'))


if __name__ == '__main__':
    app.run(debug=True)
