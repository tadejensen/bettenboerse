from wtforms import IntegerField, StringField, TextAreaField, DateField, SelectField, SubmitField
from wtforms import validators, ValidationError
from flask_wtf import FlaskForm

import bettenboerse.settings as settings


def shelter_validate_date(form, field):
    if form.data['date_to_june'] and form.data['date_from_june']:
        if not form.data['date_to_june'] > form.data['date_from_june']:
            raise ValidationError('Das End-Datum liegt vor dem Start-Datum.')


def validate_date_to(form, field):
    if form.data['date_to'] < form.data['date_from']:
        raise ValidationError('Das End-Datum liegt vor dem Start-Datum.')


def validate_date_from(form, field):
    if form.data['date_from'] < settings.start_date:
        raise ValidationError("Du kommst zu früh :)")


def validate_phone(form, field):
    phone = form.data.get('telephone', '').strip()
    if not phone.startswith("+"):
        if not phone.isnumeric():
            raise ValidationError('Die Telefonnummer muss entweder mit + und der Länderkennung anfangen oder numerisch sein')
        if phone[0] != "0":
            raise ValidationError('Die Telefonnummer muss entweder mit 0 anfangen oder + (und der Länderkennung anfangen)')



def validate_long_lat(form, field):
    # TODO: dry
    if form.data['latitude']:
        if not form.data['longitude']:
            raise ValidationError('Längen- und Breitengrad müssen angegeben werden')
        try:
            float(form.data['longitude'])
            float(form.data['longitude'])
        except ValueError:
            raise ValidationError('Falsches Format für Längen/Breitengrad-Angabe')
    if form.data['longitude']:

        try:
            float(form.data['longitude'])
            float(form.data['longitude'])
        except ValueError:
            raise ValidationError('Falsches Format für Längen/Breitengrad-Angabe')
        if not form.data['latitude']:
            raise ValidationError('Längen- und Breitengrad müssen angegeben werden')


def validate_reservation(form, field):
    total_beds = 5
    free_beds = int(form.data['free_beds'])
    state = form.data['state']
    if free_beds > total_beds:
        raise ValidationError(f'Diese Unterkunft hat nur {total_beds} Betten ({free_beds} freie Betten angegeben).')
    if free_beds == 0 and state != "FULL":
        raise ValidationError("Diese Unterkunft hat keine freien Betten mehr. Bitte Status auf 'alle Plätze belegt' setzen")
    if free_beds != total_beds and state == "FREE":
        raise ValidationError("In dieser Unterkunft schläft jemand. Falscher Status angegeben.")
    # TODO: what if PARTIL angegeben, aber ist voll oder leer
    # kann auf FULL stellen, obwohls nicht FULL ist
        # => ist gerade hardcoded auf 5
    # TODO: freien Betten anzeigen
    # reihenfolge anzeigen (freie betten weiter oben


class ShelterForm(FlaskForm):
    name = StringField(
        'Name',
        validators=[validators.InputRequired()]
    )
    pronoun = StringField(
        'Deine Pronomen',
        validators=[validators.InputRequired()]
    )
    telephone = StringField(
        'Telefonnummer',
        validators=[validators.InputRequired()]
    )
    address = StringField(
        'Wo befindet sich die Wohnung/Schlafplätze (genaue Adresse)?',
        validators=[validators.InputRequired()]
    )
    keys = TextAreaField(
        'Wie kommt Mensch in die Wohnung? Gibt es ein Versteck für den Schlüssel? Ist immer jemand da zum klingeln? Wo kann Mensch klingeln?',
        validators=[validators.InputRequired()]
    )
    rules = TextAreaField(
        'Hausregeln - was ist zu beachten (diese Info wird den Menschen weitergegeben, die dort übernachten)',
        validators=[validators.InputRequired()]
    )
    beds_basic = IntegerField(
        'Wie viele Schlafplätze kannst du anbieten, wenn Menschen Isomatte/Schlafsack mitbringen',
        validators=[validators.InputRequired(), validators.NumberRange(min=0)]
    )
    beds_luxury = IntegerField(
        'Wie viele Schlafplätze kannst du anbieten, wenn Menschen keine Isomatte/Schlafsack mitbringen (Bett, Sofa, Matratze)',
        validators=[validators.InputRequired(), validators.NumberRange(min=0)]
    )
    date_from_june = DateField(
        'Ab wann kannst du für die Aktionen im Juni Schlafplätze anbieten (wir suchen Schlafplätze ab 18.06. in Berlin)',
        validators=[validators.InputRequired()],
    )
    date_to_june = DateField(
        'Bis wann kannst du für die Aktionen im Juni Schlafplätze anbieten (Dauer: mehrere Wochen)',
        validators=[validators.InputRequired(), shelter_validate_date]
    )
    latitude = StringField(
        'Breitengrad (latitude)',
        validators=[validators.Optional(), validate_long_lat]
    )
    longitude = StringField(
        'Längengrad (longitude)',
        validators=[validators.Optional(), validate_long_lat]
    )
    internal_comment = TextAreaField(
        'Interner Kommentar (nur für Menschen, die Unterkünfte koordinieren/organisieren)',
        validators=[validators.Optional()]
    )
    area = StringField(
        'Himmelsrichtung',
        validators=[validators.Optional()]
    )


class DeleteShelterForm(FlaskForm):
    submit = SubmitField('Unterkunft löschen', validators=[validators.InputRequired()])


class MenschForm(FlaskForm):
    name = StringField("Vor- und Nachname", validators=[validators.InputRequired()])
    birthday = DateField("Geburtstagsdatum", validators=[validators.InputRequired()])
    telephone = StringField('Telefonnummer', validators=[validators.InputRequired(), validate_phone])
    relative = StringField('Angehörigen/Notfallkontakte (Name, Telefonnummer und wann die Person angerufen werden soll)', validators=[validators.Optional()])
    bezugsgruppe = StringField('Bezugsgruppe (oder auch "Support" oder "Orga", wenn das deiner Rolle eher entspricht)', validators=[validators.InputRequired()])
    date_from = DateField("Von wann bist du in Berlin?", validators=[validators.InputRequired(), validate_date_from])
    date_to = DateField("Bis wann bist du in Berlin?", validators=[validators.InputRequired(), validate_date_to])
    flinta = SelectField("Ich möchte in einem FLINTA Space unterkommen (Frauen, Lesben, intergeschlechtliche, nichtbinäre, trans und agender Personen)", choices=["Nein", "Ja"])
    non_food = StringField('Hast du Lebensmittelunverträglichkeiten?', validators=[validators.Optional()])
    needs = StringField('Hast du besondere Bedürfnisse (z. B. kannst nicht länger auf einer Isomatte schlafen, generell Barrierefreiheit)', validators=[validators.Optional()])
    fellows = StringField('Ich reise mit folgenden Menschen an/möchte mit folgenden Menschen zusammen übernachten', validators=[validators.Optional()])


class DeleteMenschForm(FlaskForm):
    submit = SubmitField('löschen', validators=[validators.InputRequired()])


class SignalAccountForm(FlaskForm):
    device_name = StringField('Name für das gelinkte Gerät', validators=[validators.DataRequired()])
    submit = SubmitField('Gerät hinzufügen', validators=[validators.InputRequired()])


class SignalMessageForm(FlaskForm):
    telephone = StringField('Weitere Empfänger*in?', validators=[validators.Optional()])
    message = TextAreaField('Nachricht', validators=[validators.DataRequired()])
    submit = SubmitField('Nachricht abschicken', validators=[validators.InputRequired()])


class FindShelterForm(FlaskForm):
    date_from = DateField("Von wann wird eine Unterkunft gesucht?", validators=[validators.InputRequired(), validate_date_from])
    date_to = DateField("Bis wann wird eine Unterkunft gesucht?", validators=[validators.InputRequired(), validate_date_to])
    beds_needed = IntegerField('Für wie viele Menschen wird eine Unterkunft benötigt?', validators=[validators.InputRequired(), validators.NumberRange(min=0)])
    submit = SubmitField('Unterkunft suchen', validators=[validators.InputRequired()])


class ReservationForm(FlaskForm):
    class Meta:
        csrf = False
    date_from = DateField("Von wann wird eine Unterkunft gesucht?", validators=[validators.InputRequired(), validate_date_from])
    date_to = DateField("Bis wann wird eine Unterkunft gesucht?", validators=[validators.InputRequired(), validate_date_to])
    #beds_needed = IntegerField('Für wie viele Menschen wird eine Unterkunft benötigt?', validators=[validators.InputRequired(), validators.NumberRange(min=0)])


class DeleteReservation(FlaskForm):
    submit = SubmitField('Reservierung entfernen', validators=[validators.InputRequired()])
