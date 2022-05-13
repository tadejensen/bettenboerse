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
    sleeping_places_basic = IntegerField(
        'Wie viele Schlafplätze kannst du anbieten, wenn Menschen ISO-Matte/Schlafsack mitbringen',
        validators=[validators.InputRequired(), validators.NumberRange(min=0)]
    )
    sleeping_places_luxury = IntegerField(
        'Wie viele Schlafplätze kannst du anbieten, wenn Menschen keine ISO-Matte/Schlafsack mitbringen',
        validators=[validators.InputRequired(), validators.NumberRange(min=0)]
    )
    date_from_may = DateField(
        'Ab wann kannst du für das Aktionswochenende im Mai Schlafplätze anbieten (wir suchen Schlafplätze ab 20.05. in Berlin)',
        validators=[validators.Optional()],
    )
    date_to_may = DateField(
        'Bis wann kannst du für das Aktionswochenende im Mai Schlafplätze anbieten (geht bis etwa 24.05.)',
        validators=[validators.Optional()],
    )
    date_from_june = DateField(
        'Ab wann kannst du für die Aktionen im Juni Schlafplätze anbieten (wir suchen Schlafplätze ab 18.06. in Berlin)',
        validators=[validators.Optional()],
    )
    date_to_june = DateField(
        'Bis wann kannst du für die Aktionen im Juni Schlafplätze anbieten (Dauer: mehrere Wochen)',
        validators=[validators.Optional()],
    )
