#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, flash, url_for, session, request
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

        if form.validate():
            menschen = Mensch.query.filter(form.date_from.data >= Mensch.date_from). \
                                    filter(form.date_to.data < Mensch.date_to).order_by(Mensch.bezugsgruppe.asc()).all()
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
            delta = timedelta(days=1)
            # check user input: Can we use the shelter in this time?
            if form.date_from.data < shelter.date_from_june or form.date_to.data > shelter.date_to_june:
                menschen = Mensch.query.all()
                flash("Die Unterkunft steht uns zu dem angegebenen Zeitraum nicht zur Verfügung", "danger")
                return render_template("bulk_reservation.html",
                                       shelter=shelter,
                                       form=form,
                                       menschen=menschen)
            stay_start = form.date_from.data
            ids_menschen_all = [m.id for m in menschen]
            ids_menschen_submitted = request.form.to_dict(flat=False).get('mensch', [])
            ids_menschen_submitted = [int(x) for x in ids_menschen_submitted]
            for id in ids_menschen_submitted:
                # user input: does the user exist. And: is the user on site during this time??
                menschen = Mensch.query.all()
                if id not in ids_menschen_all:
                    flash(f"{Mensch.query.get(id).name} ist im gewünschten Zeitraum nicht vor Ort", "danger")
                    return render_template("bulk_reservation.html",
                                           shelter=shelter,
                                           form=form,
                                           menschen=menschen)
                # check user: does the user alrady have a reservation for that day?
                while stay_start < form.date_to.data:
                    res = Reservation.query.filter_by(date=stay_start).filter_by(mensch_id=id).first()
                    if res:
                        menschen = Mensch.query.all()
                        flash(f"{Mensch.query.get(id).name} hat am {stay_start.strftime('%d.%m.')} schon eine Reservierung in der Unterkunft '{res.shelter.name}'", "danger")
                        return render_template("bulk_reservation.html",
                                               shelter=shelter,
                                               form=form,
                                               menschen=menschen)
                    stay_start += delta
            # check if there is enough space
            delta = timedelta(days=1)
            stay_begin = form.date_from.data
            while stay_begin < form.date_to.data:
                if shelter.get_capacity_by_date(stay_begin)['beds_free'] < len(ids_menschen_submitted):
                    flash(f"Unterkunft '{shelter.name}' hat am {stay_begin.strftime('%d.%m.')} nur {shelter.get_capacity_by_date(stay_begin)['beds_free']} Betten frei (angegeben wurden {len(ids_menschen_submitted)})", "danger")
                    return render_template("bulk_reservation.html",
                                           shelter=shelter,
                                           form=form,
                                           menschen=menschen,
                                           ids_menschen_submitted=ids_menschen_submitted)
                stay_begin += delta
    else:
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
        reservation = Reservation.query.filter_by(date=date).filter_by(mensch_id=id).first()
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

    return render_template(
        'mensch_show.html',
        mensch=mensch,
        reservations=reservations,
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
        if shelter.date_to_june:
            shelters_list.append(f"{shelter.name:<55} {shelter.beds_luxury + shelter.beds_basic:>4} Betten   {shelter.date_from_june} -> {shelter.date_to_june}   {(shelter.date_to_june - shelter.date_from_june).days} Tage")
        else:
            shelters_list.append(f"{shelter.name:<55} {shelter.beds_luxury + shelter.beds_basic:>4} Betten   {shelter.date_from_june} -> {shelter.date_to_june} - kein End-Datum angegeben")
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
    try:
        messages.sendDirectMessage(to_number, message)
    except Exception as e:
        status = 1
        error = str(e)
    log = SignalLog(telephone=to_number,
                    message=message,
                    status=status,
                    error=error,
                    mensch=to_mensch_id)
    db.session.add(log)
    db.session.commit()
    return (status, error)


@app.route("/signal/", methods=["GET", "POST"])
@auth.login_required
def signal_index():
    account_form = SignalAccountForm()
    send_form = SignalMessageForm()
    device_uri = None

    try:
        account = messages.get_account()
    except Exception as e:
        flash("Fehler beim Zugreifen auf die Signal-Schnittstelle", "danger")
        flash(str(e), "danger")
        return render_template("signal_index.html",
                               account=None,
                               account_form=account_form,
                               device_uri=device_uri,
                               send_form=send_form)

    if account_form.validate_on_submit():
        device_uri = messages.link_account(account_form.device_name.data)

    if send_form.validate_on_submit():
        status, error = send_signal_message(-1,
                                            send_form.telephone.data,
                                            send_form.message.data)
        if status == 0:
            flash("Die Nachricht wurde erfolgreicht verschickt", "success")
            send_form.message.data = ""
            send_form.telephone.data = ""
        else:
            flash(f"Fehler beim Senden der Nachricht an {send_form.telephone.data}", "danger")
            flash(error, "danger")

    return render_template("signal_index.html",
                           account=account,
                           account_form=account_form,
                           device_uri=device_uri,
                           send_form=send_form)


@app.route("/signal/log")
@auth.login_required
def signal_log():
    logs = SignalLog.query.all()
    return render_template("signal_logs.html", logs=logs)


#@app.route("/shell")
#@auth.login_required
#def shell():
#    m = Mensch.query.first()
#    s = Shelter.query.first()
#    r = Reservation(mensch=m, shelter=s, date=datetime(day=21, month=7, year=2022))
#    db.session.add(r)
#    db.session.commit()
#    return "ok"


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


@app.route('/test', methods=['GET', 'POST'])
def test():
    return render_template('test.html')


@app.errorhandler(404)
def page_not_found(description):
    return render_template("error.html", description=description), 404


if __name__ == '__main__':
    app.run(debug=True)
    #app.run(host="0.0.0.0", port=22000, debug=True)
