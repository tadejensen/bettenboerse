from wtforms import IntegerField, StringField, TextAreaField, DateField, SelectField, SubmitField
from wtforms import validators, ValidationError
from flask_wtf import FlaskForm

from models import ReservationState


def validate_date(form, field):
    if form.data['date_to_june'] and form.data['date_from_june']:
        if not form.data['date_to_june'] > form.data['date_from_june']:
            raise ValidationError('Das End-Datum liegt vor dem End-Datum.')


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
        'Name*',
        validators=[validators.InputRequired()]
    )
    pronoun = StringField(
        'Deine Pronomen*',
        validators=[validators.InputRequired()]
    )
    telephone = StringField(
        'Telefonnummer*',
        validators=[validators.InputRequired()]
    )
    address = StringField(
        'Wo befindet sich die Wohnung/Schlafplätze (genaue Adresse)?*',
        validators=[validators.InputRequired()]
    )
    keys = TextAreaField(
        'Wie kommt Mensch in die Wohnung? Gibt es ein Versteck für den Schlüssel? Ist immer jemand da zum klingeln? Wo kann Mensch klingeln?*',
        validators=[validators.InputRequired()]
    )
    rules = TextAreaField(
        'Hausregeln - was ist zu beachten (diese Info wird den Menschen weitergegeben, die dort übernachten)*',
        validators=[validators.InputRequired()]
    )
    sleeping_places_basic = IntegerField(
        'Wie viele Schlafplätze kannst du anbieten, wenn Menschen Isomatte/Schlafsack mitbringen*',
        validators=[validators.InputRequired(), validators.NumberRange(min=0)]
    )
    sleeping_places_luxury = IntegerField(
        'Wie viele Schlafplätze kannst du anbieten, wenn Menschen keine Isomatte/Schlafsack mitbringen*',
        validators=[validators.InputRequired(), validators.NumberRange(min=0)]
    )
    date_from_june = DateField(
        'Ab wann kannst du für die Aktionen im Juni Schlafplätze anbieten (wir suchen Schlafplätze ab 18.06. in Berlin)*',
        validators=[validators.InputRequired()],
    )
    date_to_june = DateField(
        'Bis wann kannst du für die Aktionen im Juni Schlafplätze anbieten (Dauer: mehrere Wochen)',
        validators=[validators.Optional(), validate_date]
    )
    latitude = StringField(
        'Breitengrad (latitude)',
        validators=[validators.Optional(), validate_long_lat]
    )
    longitude = StringField(
        'Längengrad (longitude)',
        validators=[validators.Optional(), validate_long_lat]
    )
    lg_comment = TextAreaField(
        'Interner Kommentar',
        validators=[validators.Optional()]
    )


class ReservationForm(FlaskForm):
    reservation = TextAreaField("Wer schläft hier nachts?")
    #state = SelectField('Belegung für diese Nacht', choices=[(s.name, s.value[1]) for s in ReservationState])
    # TODO:add/fix validator: validate_reservation
    #free_beds = IntegerField('Wie viele Menschen können hier heute Nacht noch schlafen?',
    #                         validators=[validators.InputRequired(), validators.NumberRange(min=0)])


class DeleteShelter(FlaskForm):
    submit = SubmitField('Unterkunft löschen', validators=[validators.InputRequired()])


class MenschForm(FlaskForm):
    name = StringField('Name', validators=[validators.InputRequired()])
    telephone = StringField('Telefonnummer', validators=[validators.InputRequired()])
    bezugsgruppe = StringField('Bezugsgruppe', validators=[validators.InputRequired()])


class DeleteMensch(FlaskForm):
    submit = SubmitField('löschen', validators=[validators.InputRequired()])
