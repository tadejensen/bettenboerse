from wtforms import IntegerField, StringField, TextAreaField, DateField
from wtforms import validators
from flask_wtf import FlaskForm


class SleepingPlaceForm(FlaskForm):
    name = StringField(
        'Name',
        validators=[validators.InputRequired()]
    )
    pronoun = StringField(
        'Deine Pronomen',
        validators=[validators.InputRequired()]
    )
    telephone = StringField(
        'Telefon-Nr',
        validators=[validators.InputRequired()]
    )
    address = StringField(
        'Wo befindet sich die Wohnung/Schlafplätze (genaue Adresse)?',
        validators=[validators.InputRequired()]
    )
    keys = TextAreaField(
        'Wie kommt Mensch in die Wohnung? Gibt es ein Versteck für den Schlüssel? Ist immer jemand da zum klingeln? Wo klingeln Menschen besten klingeln?',
        validators=[validators.InputRequired()]
    )
    rules = TextAreaField(
        'Hausregeln - was ist zu beachten (diese Info wird den Menschen weitergegeben, die dort übhernachten)',
        validators=[validators.InputRequired()]
    )
    sleeping_places_basic = IntegerField(
        'Wie viele Schlafplätze kannst du anbieten, wenn Menschen ISO-Matte/Schlafsack mitbringen',
        validators=[validators.InputRequired(), validators.NumberRange(min=0)]
    )
    sleeping_places_luxury = IntegerField(
        'Wie viele Schlafplätze kannst du anbieten, wenn Menschen keine ISO-Matte/Schlafsack mitbringen',
        validators=[validators.InputRequired(), validators.NumberRange(min=0)]
    )
    date_from_march = DateField(
        'Ab wann kannst du für den Marsch im Mai Schlafplätze anbieten (wir suchen ab 20.05.)',
        validators=[validators.Optional()],
    )
    date_to_march = DateField(
        'Bis wann kannst du für den Marsch im Mai Schlafplätze anbieten (der Marsch endet am 23.05.)',
        validators=[validators.Optional()],
    )
    date_from_june = DateField(
        'Ab wann kannst du für die Aktionen im Juni Schlafplätze anbieten (benötigt wird ab 18.06.)',
        validators=[validators.Optional()],
    )
    date_to_june = DateField(
        'Bis wann kannst du für den Marsch im Juni Schlafplätze anbieten (Dauer: mehrere Wochen)',
        validators=[validators.Optional()],
    )
