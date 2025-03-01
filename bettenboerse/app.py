#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import timedelta, date, datetime
import threading
from flask import Flask, render_template, redirect, flash, url_for, session, request
from markupsafe import Markup
from flask_httpauth import HTTPBasicAuth
from flask_migrate import Migrate
from werkzeug.security import check_password_hash
from bettenboerse.forms import ShelterForm, DeleteShelterForm, MenschForm, DeleteMenschForm, SignalAccountForm, SignalMessageForm, FindShelterForm, ReservationForm, DeleteReservation
import uuid
from flask_qrcode import QRcode
from collections import OrderedDict
import string
import random
import waitress

import bettenboerse.settings as settings

from bettenboerse.models import Shelter, Reservation, Mensch, SignalLog

import bettenboerse.messages as messages

print(f"Database location: {settings.DB_LOCATION}")
app = Flask(__name__)
app.config['SECRET_KEY'] = settings.FLASK_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = settings.DB_LOCATION
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

QRcode(app)
auth = HTTPBasicAuth()

from bettenboerse.models import db

migrate = Migrate(app, db, compare_type=True, render_as_batch=True)

db.init_app(app)
with app.app_context():
    db.create_all()


@app.route('/unterkunft-finden', methods=['GET', 'POST'])
@auth.login_required
def find_shelter():
    shelters_ok = []
    form = FindShelterForm()
    if form.validate_on_submit():
        stay_begin = form.date_from.data
        shelters = Shelter.query.filter(stay_begin >= Shelter.date_from_june). \
                                 filter(form.date_to.data <= Shelter.date_to_june). \
                                 order_by(Shelter.beds_total.desc()).all()
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
        today=date.today()
    )


@app.route('/unterkunft/<uuid>/reservieren', methods=['GET', 'POST'])
@auth.login_required
def edit_reservation_bulk(uuid):
    shelter = Shelter.query.get_or_404(uuid, description=f"Unterkunft mit der id {uuid} wurde nicht gefunden")

    if request.method == "GET":
        form = ReservationForm(request.args)

        if "beds_needed" in request.args.keys() and form.validate():
            menschen = Mensch.query.filter(form.date_from.data >= Mensch.date_from). \
                                    filter(form.date_to.data <= Mensch.date_to). \
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
                    res = Reservation.query.filter_by(date=stay_begin).filter_by(mensch_id=id).filter_by(shelter=shelter).first()
                    if not res:
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


@app.route('/unterkunft/<uuid>/reservation/<day>/edit', methods=['GET', 'POST'])
@auth.login_required
def edit_reservation(uuid, day):
    shelter = Shelter.query.get_or_404(uuid, description=f"Unterkunft mit der id {uuid} wurde nicht gefunden")
    # TODO: check if for start und end (between from and to)
    try:
        day = datetime.strptime(day, "%d.%m.%Y").date()
    except ValueError:
        return render_template("error.html", description="Datum im falschen Format angegeben. TT.MM.YYYY"), 400

    menschen = Mensch.query.filter(day >= Mensch.date_from).filter(day < Mensch.date_to).order_by(Mensch.bezugsgruppe.asc()).all()

    reservations_per_day = Reservation.query.filter_by(shelter=shelter).filter_by(date=day).all()
    reservations_menschen_ids = [reservation.mensch.id for reservation in reservations_per_day]
    if request.method == "GET":
        return render_template(
            'reservation_edit.html',
            uuid=uuid,
            date=day,
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
                date=day,
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
            date=day,
            menschen=menschen,
            shelter=shelter,
            reservations_menschen_ids=ids_menschen_submitted,
        )

    # check: is there already a reservation for a Mensch for that day?
    for id in ids_menschen_submitted:
        reservation = Reservation.query.filter_by(date=day).filter_by(mensch_id=id).filter(Reservation.shelter != shelter).first()
        if reservation:
            mensch = Mensch.query.get(id)
            flash(f"{mensch.name} hat bereits eine Übernachtung für diesen Tag bei {reservation.shelter.name}", "danger")
            return render_template(
                'reservation_edit.html',
                uuid=uuid,
                date=day,
                menschen=menschen,
                shelter=shelter,
                reservations_menschen_ids=ids_menschen_submitted,
            )
    # TODO: is the user on site for that day?

    Reservation.query.filter_by(shelter=shelter).filter_by(date=day).delete()
    for mensch_id in ids_menschen_submitted:
        mensch = Mensch.query.get(int(mensch_id))
        reservation = Reservation.query.filter_by(shelter=shelter).filter_by(date=day).filter_by(mensch=mensch).first()
        if not reservation:
            reservation = Reservation(shelter=shelter, date=day, mensch=mensch)
    db.session.commit()

    return redirect(url_for('show_shelter',
                            uuid=uuid,
                            _anchor=f"reservierung-{day.strftime('%d%m')}"))


@app.route('/unterkunft/<uuid>/reservation/<mensch_id>/<day>/delete', methods=['GET', 'POST'])
@auth.login_required
def delete_reservation(uuid, mensch_id, day):
    shelter = Shelter.query.get_or_404(uuid, description=f"Unterkunft mit der id {uuid} wurde nicht gefunden")
    mensch = Mensch.query.get_or_404(mensch_id, description=f"Mensch mit der id {uuid} wurde nicht gefunden")
    try:
        day = datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError:
        return render_template("error.html", description="Datum im falschen Format angegeben. TT.MM.YYYY")

    form = DeleteReservation()
    if form.validate_on_submit():
        reservation = Reservation.query.filter_by(date=day). \
                                        filter_by(mensch=mensch). \
                                        filter_by(shelter=shelter).first()
        if not reservation:
            flash("Keine Reservierung gefunden", "danger")
            return render_template(
                'reservation_delete.html',
                shelter=shelter,
                mensch=mensch,
                form=form,
                day=day)
        db.session.delete(reservation)
        db.session.commit()
        flash(f"Die Reservierung für {mensch.name} wurde entfernt", "success")
        return redirect(url_for('show_shelter',
                                uuid=uuid,
                                _anchor=f"reservierung-{day.strftime('%d%m')}"))
    return render_template(
        'reservation_delete.html',
        shelter=shelter,
        mensch=mensch,
        form=form,
        day=day,
    )



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
    day = request.args.get("date")
    if day:
        try:
            day = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            return render_template("error.html", description="Datum im falschen Format angegeben. TT.MM.YYYY")
        shelters = Shelter.query.filter(Shelter.date_from_june <= day).filter(Shelter.date_to_june > day).all()
    else:
        shelters = Shelter.query.all()
    empty_shelters = []
    complete_shelters = []
    for shelter in shelters:
        if shelter.latitude and len(shelter.latitude) > 0:
            complete_shelters.append(shelter)
        else:
            empty_shelters.append(shelter)
    shelters_without_area = Shelter.query.filter_by(area="").all()
    return render_template('map.html',
                           empty_shelters=empty_shelters,
                           complete_shelters=complete_shelters,
                           shelters_without_area=shelters_without_area,
                           date=day)


@app.route('/übersicht')
@auth.login_required
def overview():
    shelters = Shelter.query.order_by(Shelter.beds_total.desc()).all()
    shelters_list = []
    for shelter in shelters:
        shelters_list.append(f"{shelter.name:<55} {shelter.beds_luxury + shelter.beds_basic:>4} Betten   {shelter.date_from_june.strftime('%a %d.%m.')} -> "
                             f"{shelter.date_to_june.strftime('%a %d.%m.')}   {(shelter.date_to_june - shelter.date_from_june).days} Nächte")
    delta = timedelta(days=1)

    start = settings.start_date
    end = settings.end_date
    beds = {}

    while start < end:
        used_beds = Reservation.query.filter_by(date=start).count()
        shelters = Shelter.query.filter(start >= Shelter.date_from_june).filter(start < Shelter.date_to_june).all()
        menschen = Mensch.query.filter(start >= Mensch.date_from).filter(start < Mensch.date_to).count()
        beds_total = sum([s.beds_total for s in shelters])
        beds[start] = {'beds_total': beds_total, 'used_beds': used_beds, 'shelters': shelters, 'menschen_on_site': menschen}
        start += delta

    return render_template("übersicht.html", beds=beds, shelters=shelters_list, today=date.today())


def send_signal_message(to_mensch_id, to_number, message, tag):
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
                        mensch_id=to_mensch_id,
                        tag=tag)
        db.session.add(log)
        db.session.commit()
        return (status, error)


def generate_user_notification_text(user_id):
    delta = timedelta(days=1)
    stays = OrderedDict()
    mensch = Mensch.query.get(user_id)
    reservations = Reservation.query.filter_by(mensch=mensch).order_by(Reservation.date.asc())
    msg = f"+++ WICHTIG: deine Unterkunft in Berlin+++\n\nHallo { mensch.name },\nhier ist die Bettenbörse der Letzten Generation. Folgende Übernachtungen sind aktuell für dich vorgesehen:\n"
    for r in reservations:
        if r.shelter not in stays.keys():
            stays[r.shelter] = []
        stays[r.shelter].append(r.date)
    for shelter, dates in stays.items():
        url = settings.BASE_URL + url_for('show_shelter', uuid=shelter.uuid)
        start = dates[0]
        end = dates[-1] + delta
        msg += f"Unterkunft für die Zeit von {start.strftime('%d.%m. (%A)')} bis {end.strftime('%d.%m. (%A)')}:\n" + url + "\n"
    msg += """Für jede Unterkunft soll es eine Person geben, die den Kontakt zur Gastgeber*in aufnehmen soll, um den Zugang zur Wohnung zu klären. So entlasten wir den*die Gastgeber*innen..
XXX ENTWEDER
- WICHTIG: Diese Person bist du. Kannst du dich bitte darum kümmern? Wenn ja, bestätige uns das bitte so schnell wie möglich (01521 04 00 488 anrufen/schreiben). Deine Aufgabe ist es, zu organisieren, wie du Zugang zur Wohnung bekommst, indem du den*die Gastgeber*in anrufst. Weitere Menschen, die in der Unterkunft wohnen, würden dich als primäre Ansprechperson kontaktieren, um den Zugang zur Wohhung zu klären.
XXX ODER
- Bitte nehme vor deiner Anreise Kontakt mit Menschen der Letzten Generation auf, die dort bereits wohnen. Eine entsprechende Liste an Menschen und deren Telefonnummern findest du in der Bettenbörse (siehe Link oben). Jede Unterkunft hat eine verantwortliche Person, die dir im Zweifelsfall Details zum Zugang geben kann. Für deine Unterkunft ist das XXX (Telefonnummer findest du auch in der Bettenbörse - siehe Link oben).\n
- Denke an Zelt/Isomatte/Schlafsack. Auch wenn du in einem Bett schläfst, wäre es hilfreich, wenn du dein Camping Equipment verleihen kannst.
- Erinnere dich an deinen Auszugstermin, wir werden dir KEINE Erinnerung schicken (überlege dir auch, ob du da vielleicht in der GeSa übernachtest - kontaktiere uns).
- Manche Menschen können nicht über einen längeren Zeitraum auf einer Isomatte schlafen. Nehmt daher bitte gegenseitig Rücksicht aufeinander und sprecht darüber.
- Falls du mehrere male in Berlin sein wirst: melde dich bitte bei uns, um uns die Daten durchzugeben. Danke :)

Zur Erinnerung: die Unterkünfte AG hat wegen der Menge an Unterkünften kein Detailwissen zu allen Wohnungen und wir müssen auf deine Eigenverantwortung als Bewohner*in setzen, um Details (z. B. zum Zutritt) zu regeln.
Wir helfen dir natürlich trotzdem gerne weiter, wenn es irgendwo hakt. Wenn du Fragen/Probleme bezüglich deiner Unterkunft hast, kannst du dich gerne bei der Nummer 01521 04 00 488 melden.

Einen guten Aufenthalt wünscht die
Unterkünfte AG der Letzten Generation 🛌💒🏡⛺️"""
    return msg


def generate_tag():
    tag = ""
    for i in range(5):
        tag += random.choice(string.ascii_letters)
    return tag


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

    if request.method == "GET":
        selected_menschen_ids = request.args.to_dict(flat=False).get('mensch', [])
        selected_menschen_ids = [int(x) for x in selected_menschen_ids]
        form = SignalMessageForm(request.args)
        notify = int(request.args.get("notify", "-1"))
        # check input
        if notify != -1:
            text = generate_user_notification_text(notify)
            form.message.data = text

        return render_template("signal_send.html",
                               account=account,
                               form=form,
                               menschen=menschen,
                               selected_menschen_ids=selected_menschen_ids)

    if form.validate_on_submit():
        ids_menschen_submitted = request.form.to_dict(flat=False).get('mensch', [])
        ids_menschen_submitted = [int(x) for x in ids_menschen_submitted]
        ids_menschen_all = [mensch.id for mensch in menschen]
        tag = generate_tag()
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
                                form.message.data,
                                tag)
            flash(Markup(f'Nachricht an {form.telephone.data} wurde verschickt. Bitte im <a href="{ url_for("signal_log", tag=tag) }">Log</a> nachschauen, obs geklappt hat (kann einen Moment brauchen)'), "primary")
        for id in ids_menschen_submitted:
            mensch = Mensch.query.get(id)
            args = (mensch.id, mensch.telephone, form.message.data, tag)
            t = threading.Thread(target=send_signal_message, args=args)
            t.start()
            flash(Markup(f'Nachricht an {mensch.name} wurde verschickt. Bitte im <a href="{ url_for("signal_log", tag=tag) }">Log</a> nachschauen, obs geklappt hat (kann einen Moment brauchen)'), "primary")

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
    tag = request.args.get('tag', None)
    messages_ok = 0
    messages_failed = 0
    if tag:
        logs = SignalLog.query.filter_by(tag=tag).order_by(SignalLog.created.desc()).all()
        messages_ok = SignalLog.query.filter(SignalLog.tag.like(tag)). \
                                      filter_by(status=0). \
                                      order_by(SignalLog.created.desc()).count()
        messages_failed = SignalLog.query.filter(SignalLog.tag.like(tag)). \
                                                 filter_by(status=1). \
                                                 order_by(SignalLog.created.desc()).count()
    else:
        logs = SignalLog.query.order_by(SignalLog.created.desc()).all()
    return render_template("signal_logs.html", logs=logs, tag=tag,
            messages_ok=messages_ok, messages_failed=messages_failed)


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


from bettenboerse.letade import hist_betten, plot_menschen, plot_calendar


@app.route("/hist_betten.png")
@auth.login_required
def api_hist_betten():
    return hist_betten(dbfile="instance/unterkünfte.db", start_plot="2022-06-18", end_plot="2022-07-20")


@app.route("/plot_menschen.png")
@auth.login_required
def api_plot_menschen():
    return plot_menschen(dbfile="instance/unterkünfte.db", start_plot="2022-06-17", end_plot="2022-07-20", today=None)


@app.route("/plot_calendar.png")
@auth.login_required
def api_plot_calendar():
    return plot_calendar(dbfile="instance/unterkünfte.db", start_plot="2022-06-18", end_plot="2022-07-20")


#@app.route('/menschen/export/csv')
#@auth.login_required
#def export_menschen_csv():
#    buffer = StringIO()
#    writer = csv.writer(buffer, delimiter='|')
#    header = ("Name", "Bezugsgruppe", "von", "bis", "Telefon", "Geburtstag", "Angehörige", "Bin da mit", "brauche FLINTA Space", "Lebensmittelunverträglichkeiten", "besondere Bedürfnisse")
#    writer.writerow(header)
#    menschen = Mensch.query.all()
#    for m in menschen:
#        row = (m.name, m.bezugsgruppe, m.date_from, m.date_to, m.telephone,
#               m.birthday, m.relative, m.fellows, m.flinta, m.non_food, m.needs)
#        writer.writerow(row)
#    filename = f"bettenbörse_menschen_{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
#    resp = make_response(buffer.getvalue())
#    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
#    resp.headers["Content-type"] = "text/csv"
#    return resp


@app.errorhandler(404)
def page_not_found(description):
    return render_template("error.html", description=description), 404


@app.route('/reservierungen')
@auth.login_required
def show_reservations():
    day = request.args.get("date", date.today())
    if type(day) == str:
        try:
            day = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            flash("Das Datum wurde im falschen Format angegeben.", "danger")
            day = date.today()
    reservations = Reservation.query.filter_by(date=day).all()
    return render_template("reservations_list.html", reservations=reservations, day=day)


def get_menschen_without_shelter_for_day(day):
    on_site_menschen = Mensch.query.filter(day >= Mensch.date_from). \
                                    filter(day < Mensch.date_to). \
                                    order_by(Mensch.bezugsgruppe.asc()).all()
    for mensch in on_site_menschen:
        if not Reservation.query.filter_by(mensch=mensch).filter_by(date=day).first():
            yield mensch


def get_moving_out_menschen():
    today = date.today()
    yesterday = today - timedelta(days=1)
    menschen = Mensch.query.all()
    for mensch in menschen:
        reservation_yesterday = Reservation.query.filter_by(mensch=mensch).filter_by(date=yesterday).first()
        reservation_today = Reservation.query.filter_by(mensch=mensch).filter_by(date=today).first()
        if reservation_yesterday and not reservation_today:
            yield mensch
        if reservation_yesterday and reservation_today and reservation_today.shelter != reservation_yesterday.shelter:
            yield mensch


def get_new_shelters_for_day(day):
    shelters = Shelter.query.filter_by(date_from_june=day).all()
    return shelters


def get_done_shelters_for_day(day):
    shelters = Shelter.query.filter_by(date_to_june=day).all()
    return shelters


def get_menschen_with_reservation_without_notification():
    for mensch in Mensch.query.all():
        reservation = Reservation.query.filter_by(mensch=mensch).count()
        notification = SignalLog.query.filter_by(mensch=mensch).first()
        if reservation and not notification:
            yield mensch


@app.route('/hinweise')
@auth.login_required
def show_warnings():
    today = date.today()
    day_delta = timedelta(days=1)
    menschen_without_shelter_for_today = get_menschen_without_shelter_for_day(today)
    menschen_without_shelter_for_tomorrow = get_menschen_without_shelter_for_day(today + day_delta)
    menschen_without_shelter_for_tomorrow_tomorrow = get_menschen_without_shelter_for_day(today + day_delta + day_delta)
    menschen_moving_out_today = get_moving_out_menschen()

    shelters_new_yesterday = get_new_shelters_for_day(today - day_delta)
    shelters_new_today = get_new_shelters_for_day(today)
    shelters_new_tomorrow = get_new_shelters_for_day(today + day_delta)

    shelters_done_yesterday = get_done_shelters_for_day(today - day_delta)
    shelters_done_today = get_done_shelters_for_day(today)
    shelters_done_tomorrow = get_done_shelters_for_day(today + day_delta)
    shelters_done_tomorrow_tomorrow = get_done_shelters_for_day(today + day_delta + day_delta)
    menschen_with_reservation_without_notification = get_menschen_with_reservation_without_notification()


    return render_template("warnings.html",
                            menschen_without_shelter_for_today=menschen_without_shelter_for_today,
                            menschen_without_shelter_for_tomorrow=menschen_without_shelter_for_tomorrow,
                            menschen_without_shelter_for_tomorrow_tomorrow=menschen_without_shelter_for_tomorrow_tomorrow,
                            shelters_new_yesterday=shelters_new_yesterday,
                            shelters_new_today=shelters_new_today,
                            shelters_new_tomorrow=shelters_new_tomorrow,
                            shelters_done_yesterday=shelters_done_yesterday,
                            shelters_done_today=shelters_done_today,
                            shelters_done_tomorrow=shelters_done_tomorrow,
                            menschen_moving_out_today=menschen_moving_out_today,
                            shelters_done_tomorrow_tomorrow=shelters_done_tomorrow_tomorrow,
                            menschen_with_reservation_without_notification=menschen_with_reservation_without_notification,
                            )



#@app.route("/test")
#def test():
#    today = date.today()
#    menschen = Mensch.query.filter(today >= Mensch.date_from).filter(today <= Mensch.date_to).all()
#    print(menschen)
#    print(len(menschen))
#    from flask import jsonify
#    #numbers = [m.telephone for m in menschen]
#    numbers = [m.name for m in menschen]
#    return jsonify(numbers)


def main():
    host = "0.0.0.0"
    port = 5000
    if __name__ == '__main__':
        app.run(debug=True,
                host=host,
                port=port)
    else:
        print(f"Running backend on {host}:{port}")
        waitress.serve(app, listen=f"{host}:{port}")


if __name__ == '__main__':
    main()
