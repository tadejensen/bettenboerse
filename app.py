#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import threading
from flask import Flask, render_template, redirect, flash, url_for, session, request, Markup
from flask_httpauth import HTTPBasicAuth
from flask_migrate import Migrate
from werkzeug.security import check_password_hash
from forms import ShelterForm, DeleteShelterForm, MenschForm, DeleteMenschForm, SignalAccountForm, SignalMessageForm, FindShelterForm, ReservationForm
from datetime import datetime, timedelta
import uuid
from flask_qrcode import QRcode

import settings

from models import Shelter, Reservation, Mensch, SignalLog

import messages

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


@app.route('/unterkunft-finden', methods=['GET', 'POST'])
@auth.login_required
def find_shelter():
    shelters_ok = []
    form = FindShelterForm()
    if form.validate_on_submit():
        stay_begin = form.date_from.data
        shelters = Shelter.query.filter(stay_begin >= Shelter.date_from_june).filter(form.date_to.data < Shelter.date_to_june).all()
        delta = timedelta(days=1)
        for shelter in shelters:
            stay_begin = form.date_from.data
            space_ok = True
            while stay_begin < form.date_to.data:
                if shelter.get_capacity_by_date(stay_begin)['beds_free'] < int(form.beds_needed.data):
                    print(f"{shelter.name} hat am {stay_begin} nur {shelter.get_capacity_by_date(stay_begin)['beds_free']} Betten frei")
                    space_ok = False
                    break
                stay_begin += delta
            if space_ok:
                shelters_ok.append(shelter)
    return render_template(
        'find_shelter.html',
        form=form,
        shelters=shelters_ok,
    )


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
        shelter.beds_basic = int(form.data['beds_basic'])
        shelter.beds_luxury = int(form.data['beds_luxury'])
        db.session.commit()
        flash("Die Änderungen wurden gespeichert", "success")
        return redirect(url_for('show_shelter', uuid=uuid))

    return render_template(
        'shelter_edit.html',
        form=form,
        shelter=shelter,
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
        settings=settings,
    )


@app.route('/unterkunft/<uuid>/reservieren', methods=['GET', 'POST'])
@auth.login_required
def edit_reservation_bulk(uuid):
    shelter = Shelter.query.get_or_404(uuid, description=f"Unterkunft mit der id {uuid} wurde nicht gefunden")

    if request.method == "GET":
        form = ReservationForm(request.args)

        if "beds_needed" in request.args.keys() and form.validate():
            menschen = Mensch.query.filter(form.date_from.data >= Mensch.date_from). \
                                    filter(form.date_to.data < Mensch.date_to). \
                                    order_by(Mensch.bezugsgruppe.asc()).all()
        else:
            menschen = Mensch.query.order_by(Mensch.bezugsgruppe.asc()).all()
        return render_template("bulk_reservation.html",
                               shelter=shelter,
                               form=form,
                               menschen=menschen)

    if request.method == "POST":
        form = ReservationForm()
        if form.validate_on_submit():
            menschen = Mensch.query.filter(form.date_from.data >= Mensch.date_from). \
                                    filter(form.date_to.data <= Mensch.date_to).all()
            # check user input: Can we use the shelter in this time?
            if form.date_from.data < shelter.date_from_june or form.date_to.data > shelter.date_to_june:
                flash("Die Unterkunft steht uns zu dem angegebenen Zeitraum nicht zur Verfügung", "danger")
                return render_template("bulk_reservation.html",
                                       shelter=shelter,
                                       form=form,
                                       menschen=menschen)

            delta = timedelta(days=1)
            stay_begin = form.date_from.data
            ids_menschen_all = [m.id for m in menschen]
            ids_menschen_submitted = request.form.to_dict(flat=False).get('mensch', [])
            ids_menschen_submitted = [int(x) for x in ids_menschen_submitted]
            # check user input: no menschen supplied?
            if ids_menschen_submitted == []:
                flash("Keine Menschen ausgewählt, die dort schlafen sollen", "danger")
                return render_template("bulk_reservation.html",
                                       shelter=shelter,
                                       form=form,
                                       menschen=menschen)
            for id in ids_menschen_submitted:
                # user input: does the user exist. And: is the user on site during this time??
                if id not in ids_menschen_all:
                    flash(f"{Mensch.query.get(id).name} ist im gewünschten Zeitraum nicht vor Ort", "danger")
                    return render_template("bulk_reservation.html",
                                           shelter=shelter,
                                           form=form,
                                           menschen=menschen)
                # check user: does the user alrady have a reservation for that day?
                while stay_begin < form.date_to.data:
                    res = Reservation.query.filter_by(date=stay_begin).filter_by(mensch_id=id).filter(Reservation.shelter != shelter).first()
                    if res:
                        flash(f"{Mensch.query.get(id).name} hat am {stay_begin.strftime('%d.%m.')} schon eine Reservierung in der Unterkunft '{res.shelter.name}'", "danger")
                        return render_template("bulk_reservation.html",
                                               shelter=shelter,
                                               form=form,
                                               menschen=menschen)
                    stay_begin += delta
            # check if there is enough space
            stay_begin = form.date_from.data
            while stay_begin < form.date_to.data:
                if shelter.get_capacity_by_date(stay_begin)['beds_free'] < len(ids_menschen_submitted):
                    flash(f"Unterkunft '{shelter.name}' hat am {stay_begin.strftime('%d.%m.')} nur noch {shelter.get_capacity_by_date(stay_begin)['beds_free']} Betten frei (angegeben wurden {len(ids_menschen_submitted)})", "danger")
                    return render_template("bulk_reservation.html",
                                           shelter=shelter,
                                           form=form,
                                           menschen=menschen,
                                           ids_menschen_submitted=ids_menschen_submitted)
                stay_begin += delta
            # all checks done - create Reservations (for each day and mensch)
            stay_begin = form.date_from.data
            while stay_begin < form.date_to.data:
                for id in ids_menschen_submitted:
                    new_reservation = Reservation(date=stay_begin,
                                                  shelter=shelter,
                                                  mensch_id=id)
                    db.session.add(new_reservation)
                    flash(f"Reservierung für {Mensch.query.get(id).name} in der Unterkunft {shelter.name} am {stay_begin.strftime('%d.%m.')} hinterlegt", "success")
                stay_begin += delta
            db.session.commit()
            return redirect(url_for('show_shelter',
                                    uuid=uuid,
                                    _anchor=f"reservierung-{form.date_from.data.strftime('%d%m')}"))
        else:
            menschen = Mensch.query.order_by(Mensch.bezugsgruppe.asc()).all()
            return render_template("bulk_reservation.html",
                                   shelter=shelter,
                                   form=form,
                                   menschen=menschen)


@app.route('/unterkunft/<uuid>/reservation/<date>/edit', methods=['GET', 'POST'])
@auth.login_required
def edit_reservation(uuid, date):
    shelter = Shelter.query.get_or_404(uuid, description=f"Unterkunft mit der id {uuid} wurde nicht gefunden")
    # TODO: check if for start und end (between from and to)
    try:
        date = datetime.strptime(date, "%d.%m.%Y").date()
    except ValueError:
        return render_template("error.html", description="Datum im falschen Format angegeben. TT.MM.YYYY"), 400

    menschen = Mensch.query.filter(date >= Mensch.date_from).filter(date < Mensch.date_to).order_by(Mensch.bezugsgruppe.asc()).all()

    reservations_per_day = Reservation.query.filter_by(shelter=shelter).filter_by(date=date).all()
    reservations_menschen_ids = [reservation.mensch.id for reservation in reservations_per_day]
    if request.method == "GET":
        return render_template(
            'reservation_edit.html',
            uuid=uuid,
            date=date,
            menschen=menschen,
            shelter=shelter,
            reservations_menschen_ids=reservations_menschen_ids,
        )

    ids_menschen_all = [m.id for m in menschen]
    ids_menschen_submitted = request.form.to_dict(flat=False).get('mensch', [])
    ids_menschen_submitted = [int(x) for x in ids_menschen_submitted]

    for id in ids_menschen_submitted:
        # user input: does the user exist?
        if id not in ids_menschen_all:
            flash(f"Kein Mensch mit der id {id} zum hinzufügen gefunden", "danger")
            return render_template(
                'reservation_edit.html',
                uuid=uuid,
                date=date,
                menschen=menschen,
                shelter=shelter,
                reservations_menschen_ids=reservations_menschen_ids,
            )
            return render_template("error.html", description=f"Kein Mensch mit der id {id} zum hinzufügen gefunden"), 400

    # check: more pepole than space?
    if len(ids_menschen_submitted) > shelter.beds_total:
        flash(f"Mehr Menschen ausgewählt als Betten verfügbar ({len(ids_menschen_submitted)} ausgewählt, {shelter.beds_total} verfügbar)", "danger")
        return render_template(
            'reservation_edit.html',
            uuid=uuid,
            date=date,
            menschen=menschen,
            shelter=shelter,
            reservations_menschen_ids=ids_menschen_submitted,
        )

    # check: is there already a reservation for a Mensch for that day?
    for id in ids_menschen_submitted:
        reservation = Reservation.query.filter_by(date=date).filter_by(mensch_id=id).filter(Reservation.shelter != shelter).first()
        if reservation:
            mensch = Mensch.query.get(id)
            flash(f"{mensch.name} hat bereits eine Übernachtung für diesen Tag bei {reservation.shelter.name}", "danger")
            return render_template(
                'reservation_edit.html',
                uuid=uuid,
                date=date,
                menschen=menschen,
                shelter=shelter,
                reservations_menschen_ids=ids_menschen_submitted,
            )
    # TODO: is the user on site for that day?

    Reservation.query.filter_by(shelter=shelter).filter_by(date=date).delete()
    for mensch_id in ids_menschen_submitted:
        mensch = Mensch.query.get(int(mensch_id))
        reservation = Reservation.query.filter_by(shelter=shelter).filter_by(date=date).filter_by(mensch=mensch).first()
        if not reservation:
            reservation = Reservation(shelter=shelter, date=date, mensch=mensch)
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

    form = DeleteShelterForm()
    if form.validate_on_submit():
        db.session.delete(sp)
        db.session.commit()
        flash("Die Unterkunft wurde gelöscht", "success")
        return redirect(url_for('list_shelters'))

    return render_template(
        'shelter_delete.html',
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
    menschen = Mensch.query.order_by(Mensch.bezugsgruppe.asc())

    return render_template(
        'menschen_list.html',
        menschen=menschen,
    )


@app.route('/mensch/add', methods=['GET', 'POST'])
@app.route('/suche-schlafplatz', methods=['GET', 'POST'])
def create_mensch():
    form = MenschForm()
    if form.validate_on_submit():
        if Mensch.query.filter_by(name=form.name.data).first():
            flash(f"Es existiert bereits ein Mensch mit Namen {form.name.data}", "danger")
            return render_template(
                'mensch_add.html',
                form=form,
                settings=settings,
            )
        mensch = Mensch()
        form.populate_obj(mensch)
        db.session.add(mensch)
        db.session.commit()
        if session.get('logged_in', False) is True:
            flash("Der Mensch wurder erfolgreich angelegt", "success")
            return redirect(url_for('list_menschen'))
        else:
            flash("Dein Gesuch wurde aufgenommen", "success")
            return render_template("spenden.html")

    return render_template(
        'mensch_add.html',
        form=form,
        settings=settings,
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
        form=form,
        mensch=mensch,
    )


@app.route('/mensch/<id>/delete', methods=['GET', 'POST'])
@auth.login_required
def delete_mensch(id):
    mensch = Mensch.query.get_or_404(id, description=f"Mensch mit der id {id} wurde nicht gefunden")
    form = DeleteMenschForm()

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


@app.route('/mensch/<id>/', methods=['GET', 'POST'])
@auth.login_required
def show_mensch(id):
    mensch = Mensch.query.get_or_404(id, description=f"Mensch mit der id {id} wurde nicht gefunden")
    reservations = Reservation.query.filter_by(mensch=mensch).order_by(Reservation.date.asc()).all()
    signal_messages = SignalLog.query.filter_by(mensch=mensch).order_by(SignalLog.created.desc()).all()

    return render_template(
        'mensch_show.html',
        mensch=mensch,
        reservations=reservations,
        signal_messages=signal_messages,
    )


@app.route('/karte')
@auth.login_required
def show_map():
    date = request.args.get("date")
    if date:
        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return render_template("error.html", description="Datum im falschen Format angegeben. TT.MM.YYYY")
        shelters = Shelter.query.filter(Shelter.date_from_june <= date).filter(Shelter.date_to_june > date).all()
    else:
        shelters = Shelter.query.all()
    empty_shelters = []
    complete_shelters = []
    for shelter in shelters:
        if shelter.latitude and len(shelter.latitude) > 0:
            complete_shelters.append(shelter)
        else:
            empty_shelters.append(shelter)
    return render_template('map.html',
                           empty_shelters=empty_shelters,
                           complete_shelters=complete_shelters,
                           date=date)


@app.route('/übersicht')
@auth.login_required
def overview():
    shelters = Shelter.query.order_by(Shelter.beds_total.desc()).all()
    shelters_list = []
    for shelter in shelters:
        shelters_list.append(f"{shelter.name:<55} {shelter.beds_luxury + shelter.beds_basic:>4} Betten   {shelter.date_from_june.strftime('%a %d.%m.')} -> "
                             f"{shelter.date_to_june.strftime('%a %d.%m.')}   {(shelter.date_to_june - shelter.date_from_june).days} Tage")
    delta = timedelta(days=1)

    start = settings.start_date
    end = settings.end_date
    beds = {}

    while start < end:
        used_beds = Reservation.query.filter_by(date=start).count()
        shelters = Shelter.query.filter(start >= Shelter.date_from_june).filter(start < Shelter.date_to_june).all()
        menschen = Mensch.query.filter(start >= Mensch.date_from).filter(start <= Mensch.date_to).count()
        beds_total = sum([s.beds_total for s in shelters])
        beds[start] = {'beds_total': beds_total, 'used_beds': used_beds, 'shelters': shelters, 'menschen_on_site': menschen}
        start += delta

    return render_template("übersicht.html", beds=beds, shelters=shelters_list)


def send_signal_message(to_mensch_id, to_number, message):
    status = 0
    error = ""
    with app.app_context():
        try:
            messages.sendDirectMessage(to_number, message)
            pass
        except Exception as e:
            status = 1
            error = str(e)
        log = SignalLog(telephone=to_number,
                        message=message,
                        status=status,
                        error=error,
                        mensch_id=to_mensch_id)
        db.session.add(log)
        db.session.commit()
        return (status, error)


@app.route("/signal/send", methods=["GET", "POST"])
@auth.login_required
def signal_send_message():
    form = SignalMessageForm()
    menschen = Mensch.query.order_by(Mensch.bezugsgruppe.asc())

    try:
        account = messages.get_account()
    except Exception as e:
        flash("Fehler beim Zugreifen auf die Signal-Schnittstelle", "danger")
        flash(str(e), "danger")
        return redirect(url_for('signal_index'))
    if form.validate_on_submit():

        ids_menschen_submitted = request.form.to_dict(flat=False).get('mensch', [])
        ids_menschen_submitted = [int(x) for x in ids_menschen_submitted]
        ids_menschen_all = [mensch.id for mensch in menschen]
        for id in ids_menschen_submitted:
            # user input: does the user exist
            if id not in ids_menschen_all:
                flash(f"Mensch mit der id {id} existiert nicht", "danger")
                return render_template("signal_send.html",
                                       account=account,
                                       form=form,
                                       menschen=menschen)
        if len(form.telephone.data) > 0:
            send_signal_message(-1,
                                form.telephone.data,
                                form.message.data)
            flash(Markup(f'Nachricht an {form.telephone.data} wurde verschickt. Bitte im <a href="{ url_for("signal_log") }">Log</a> nachschauen, obs geklappt hat (kann einen Moment brauchen)'), "primary")
        for id in ids_menschen_submitted:
            mensch = Mensch.query.get(id)
            args = (mensch.id, mensch.telephone, form.message.data)
            t = threading.Thread(target=send_signal_message, args=args)
            t.start()
            flash(Markup(f'Nachricht an {mensch.name} wurde verschickt. Bitte im <a href="{ url_for("signal_log") }">Log</a> nachschauen, obs geklappt hat (kann einen Moment brauchen)'), "primary")

        # mit ner GET-Request sollen selected übergeben werden (Nachricht und Mensch(en)
        # wenn nur an 3 User => schicks direkt, ansonsten in nem neuen Thread und verweis auf das Log
        form.message.data = ""
        form.telephone.data = ""
    return render_template("signal_send.html",
                           account=account,
                           form=form,
                           menschen=menschen)


@app.route("/signal/", methods=["GET", "POST"])
@auth.login_required
def signal_index():
    form = SignalAccountForm()
    device_uri = None

    try:
        account = messages.get_account()
    except Exception as e:
        flash("Fehler beim Zugreifen auf die Signal-Schnittstelle", "danger")
        flash(str(e), "danger")
        return render_template("signal_index.html",
                               account=None,
                               form=form,
                               device_uri=device_uri)

    if form.validate_on_submit():
        device_uri = messages.link_account(form.device_name.data)

    return render_template("signal_index.html",
                           account=account,
                           form=form,
                           device_uri=device_uri)


@app.route("/signal/log")
@auth.login_required
def signal_log():
    logs = SignalLog.query.order_by(SignalLog.created.desc()).all()
    return render_template("signal_logs.html", logs=logs)


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


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from datetime import timedelta
import sqlite3
import io
from flask import Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from flask import Flask


def read_sqlite(dbfile):
    with sqlite3.connect(dbfile) as dbcon:
        #tables = list(pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", dbcon)['name'])
        tables = ["shelter", "reservation"]
        out = {tbl: pd.read_sql_query(f"SELECT * from {tbl}", dbcon) for tbl in tables}
        return out


def format_name(name, linelen=20):
    lines = int(np.ceil(len(name) / linelen))
    charperline = int(len(name) / lines)
    ukname = ""
    for line in range(lines):
        namefitzel = name[line * charperline:(line + 1) * charperline]
        if line != lines - 1:
            namefitzel = namefitzel + "-\n"
        ukname = ukname + namefitzel

    return ukname


@app.route("/hist_betten.png")
def hist_betten(dbfile="unterkünfte.db", start_plot="2022-06-18", end_plot="2022-07-15"):
    a = read_sqlite(dbfile)
    start = pd.to_datetime("2022-06-18")
    end_plot = pd.to_datetime(end_plot)
    start_plot = pd.to_datetime(start_plot)

    betten = pd.DataFrame(a["shelter"])
    reservations = pd.DataFrame(a["reservation"])

    fig_hist = plt.figure(tight_layout=True, figsize=(13, 7))
    ax_hist = plt.subplot(111)

    bedcounts = []

    t1_max = max(pd.to_datetime(betten["date_to_june"]))

    for i in range((t1_max - start).days):
        day = start + timedelta(days=i)
        valbeds = betten[(pd.to_datetime(betten["date_from_june"]) <= day) & (pd.to_datetime(betten["date_to_june"]) > day)]
        valbedcount = np.sum([valbeds["beds_basic"], valbeds["beds_luxury"]])
        bedcounts.append((i, valbedcount))

    reservations["date"] = pd.to_datetime(reservations["date"])
    resdates = set(reservations["date"])
    resdates_ind = []
    resplaces = []

    for date in resdates:
        resdates_ind.append((date - start).days)
        reses = reservations[reservations["date"] == date]
        date_ind = (date-start).days
        for ind in reses.index:
            res = reses.loc[ind]
            rescount = len(reses)
        resplaces.append((date_ind, rescount))

    bedcounts = np.array(bedcounts)
    resplaces = np.array(resplaces)

    ax_hist.bar(bedcounts[:, 0], bedcounts[:, 1], color="lightgreen", zorder=2.11, label="gesamt")
    ax_hist.bar(resplaces[:, 0], resplaces[:, 1], zorder=2.12, color="lightcoral", label="belegt")

    OG_xlim = ax_hist.get_xlim()
    ax_hist.set_xticks(np.arange(0, (t1_max - start).days, 5))

    xticklabs = []
    for tick in ax_hist.get_xticks():
        date = start + timedelta(days=int(tick))

        xticklabs.append(date.strftime("%d. %B"))
    ax_hist.set_yticks(np.arange(0, np.max(ax_hist.get_yticks()), 5), minor=True)
    ax_hist.yaxis.grid()
    ax_hist.yaxis.grid(which="minor", alpha=.25)

    xlim = ((start_plot-start).days-.5, (end_plot-start).days+.5)

    ax_hist.set(xticklabels=xticklabs, xlim=xlim,
                xlabel="Datum", ylabel="Schlafplätze")
    ax_hist.legend()
    ax_hist.xaxis.set_tick_params(rotation=45)

    output = io.BytesIO()
    FigureCanvas(fig_hist).print_png(output)
    return Response(output.getvalue(), mimetype="image/png")


@app.route("/plot_calendar.png")
def plot_calendar(dbfile="unterkünfte.db", start_plot="2022-06-18", end_plot="2022-07-15"):
    """
    dbfile: str zu unterkuefte.db
    start_date: str im Format 'yyyy-mm-dd'
        linke Anzeigegrenze des Plots
    end_date:

    """

    a = read_sqlite(dbfile)
    start = pd.to_datetime("2022-06-18")
    end_plot = pd.to_datetime(end_plot)
    start_plot = pd.to_datetime(start_plot)

    betten = pd.DataFrame(a["shelter"])
    reservations = pd.DataFrame(a["reservation"])
    # reshuman = pd.DataFrame(a["reservations_mensch"])
    # humans = pd.DataFrame(a["menschen"])

    height = 1
    legend_elements = [Patch(facecolor="lightgreen", edgecolor="none", label="frei Isomatte"),
                       Patch(facecolor="tab:green", edgecolor="none", label="frei Isomatte"),
                       Patch(facecolor="lightcoral", edgecolor="none", label="belegt")]

    fig_cal = plt.figure(tight_layout=True, figsize=(13, 8))
    ax_cal = plt.subplot()

    k = 0
    t1_max = pd.to_datetime("2022-06-18")

    yticks = []
    yticklabs = []

    for ind in betten.index:
        unterkunft = betten.loc[ind]
        ax_cal.axhline(k, ls="dashed", color="grey", lw=.75)
        k += .4 * height
        bed = unterkunft["beds_luxury"]
        iso = unterkunft["beds_basic"]
        ukname = format_name(unterkunft["name"])
        yticklabs.append(f'{ukname} ({bed + iso})')
        yticks.append(k + (bed + iso) / 2)

        t0 = pd.to_datetime(unterkunft["date_from_june"])
        t1 = pd.to_datetime(unterkunft["date_to_june"])

        if t1 is None:
            print(f"Unterkunft von {unterkunft['name']} hat kein Enddatum angegeben. 2. Juli angenommen.")
            t1 = pd.to_datetime("2022-07-02")

        t1_max = max(t1, t1_max)

        if unterkunft["uuid"] in list(reservations["shelter_id"]):
            reses = reservations[reservations["shelter_id"] == unterkunft["uuid"]]
            datecounts = reses.date.value_counts()
            for resdate in datecounts.index:
                datecount = datecounts.loc[resdate]
                resdate = pd.to_datetime(resdate)
                resdate_ind = (resdate-start).days

                ax_cal.add_patch(Rectangle((resdate_ind + .5, k), 1, datecount * height,
                                 facecolor="lightcoral", edgecolor="none", zorder=3))

        for bedi in range(bed):
            ax_cal.add_patch(Rectangle(((t0 - start).days + .5, k), (t1 - t0).days, height, facecolor="tab:green",
                                       edgecolor="none", zorder=2))
            ax_cal.add_patch(Rectangle(((t0 - start).days + .5, k), (t1 - t0).days, height, facecolor="none",
                                       edgecolor="grey", lw=.5, zorder=3.5))
            k += height
        for isoi in range(iso):
            ax_cal.add_patch(Rectangle(((t0 - start).days + .5, k), (t1 - t0).days, height, facecolor="lightgreen",
                                       edgecolor="none", zorder=2))
            ax_cal.add_patch(Rectangle(((t0 - start).days + .5, k), (t1 - t0).days, height, facecolor="none",
                                       edgecolor="grey", lw=.5, zorder=3.5))
            k += height

        k += .4 * height

    fig_cal.set_size_inches(13, k * .075)

    ax_cal.legend(handles=legend_elements)
    ax_cal.xaxis.grid(zorder=1)
    ax_cal.set(xlim=((start_plot-start).days - 1, (end_plot - start).days + 1), ylim=(0, k + .5),
               xlabel="Datum",
               yticks=yticks, yticklabels=yticklabs)

    ax_cal.set_xticks(np.arange(0, (t1_max - start).days, 5))
    ax_cal.set_xticks(np.arange((t1_max - start).days), minor=True)
    ax_cal.xaxis.grid(which="minor", zorder=1, alpha=.25)
    dates = []
    for d in ax_cal.get_xticks():
        day = start + timedelta(days=int(d))

        dates.append(day.strftime("%d. %B"))

    ax_cal.xaxis.set_tick_params(rotation=45)
    ax_cal.set(xticklabels=dates, xlim=((start_plot-start).days - 1, (end_plot - start).days + 1), ylim=(.001, k + .5))
    output = io.BytesIO()
    FigureCanvas(fig_cal).print_png(output)
    return Response(output.getvalue(), mimetype="image/png")


@app.errorhandler(404)
def page_not_found(description):
    return render_template("error.html", description=description), 404


if __name__ == '__main__':
    app.run(debug=True)
    #app.run(host="0.0.0.0", port=22000, debug=True)
