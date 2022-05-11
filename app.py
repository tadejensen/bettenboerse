#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, flash
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from forms import SleepingPlaceForm
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
    date_from_march = db.Column(db.DateTime())
    date_to_march = db.Column(db.DateTime())
    date_from_june = db.Column(db.DateTime())
    date_to_june = db.Column(db.DateTime())


# this needs to be placed here!
db.init_app(app)
db.create_all(app=app)


@auth.verify_password
def verify_password(username, password):
    if username == settings.USER and \
            check_password_hash(settings.PASSWORD_HASH, password):
        return username


@app.route('/', methods=['GET', 'POST'])
def index():
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
            date_from_march=form.data['date_from_march'],
            date_to_march=form.data['date_to_march'],
            date_from_june=form.data['date_from_june'],
            date_to_june=form.data['date_to_june'])

        db.session.add(new_sp)
        db.session.commit()
        flash("Danke, wir haben deinen Schlafplatz aufgenommen. Vielen Dank für deine Unterstützung!", "success")
        return redirect('/')

    return render_template(
        'index.html',
        form=form,
    )


@app.route('/unterkunft/<uuid>/show')
def show_sleeping_place(uuid):
    sleeping_place = SleepingPlace.query.filter_by(uuid=uuid).first()

    return render_template(
        'detail_show.html',
        sleeping_place=sleeping_place,
        base_url=settings.BASE_URL
    )


@app.route('/unterkünfte')
@auth.login_required
def show_all_sleeping_places():
    sleeping_places = SleepingPlace.query

    return render_template(
        'list.html',
        sleeping_places=sleeping_places
    )


if __name__ == '__main__':
    app.run(debug=True)
