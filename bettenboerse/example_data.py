from datetime import date
import uuid
from numpy.random import randint, choice
from ipydex import IPS

from bettenboerse.models import Shelter, Reservation, Mensch, db
import settings

from flask import Flask
import contextlib
from sqlalchemy import MetaData


app = Flask(__name__)
app.config['SECRET_KEY'] = settings.FLASK_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = settings.DB_LOCATION
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

shelter_data = [
    {
        "uuid": str(uuid.uuid4()),
        "name": "Friedrich M.",
        "pronoun": "sie/ihr",
        "telephone": "0351 123456",
        "address": "Königsbrücker Straße 12, 01099 Dresden",
        "keys": "Haupteingang, Zimmerschlüssel",
        "rules": "Nachtruhe ab 22 Uhr, keine Haustiere",
        "beds_basic": 2,
        "beds_luxury": 2,
        "date_from_june": date(2025, 6, 1),
        "date_to_june": date(2025, 6, 10),
        "latitude": "51.0651",
        "longitude": "13.7418",
        "internal_comment": "Neue Matratzen am 30. Mai geliefert",
        "area": "Neustadt"
    },
    {
        "uuid": str(uuid.uuid4()),
        "name": "Christian L.",
        "pronoun": "er/ihn",
        "telephone": "0351 654321",
        "address": "Bautzner Straße 45, 01099 Dresden",
        "keys": "Code für Tür, Schlüssel für Spind",
        "rules": "Kein Alkohol, keine Besucher nach 20 Uhr",
        "beds_basic": 3,
        "beds_luxury": 5,
        "date_from_june": date(2025, 6, 8),
        "date_to_june": date(2025, 6, 20),
        "latitude": "51.0645",
        "longitude": "13.7631",
        "internal_comment": "Tägliche Reinigung durch Externen",
        "area": "Äußere Neustadt"
    },
    {
        "uuid": str(uuid.uuid4()),
        "name": "Olaf S.",
        "pronoun": "sie/ihr",
        "telephone": "0351 888888",
        "address": "Pfotenhauerstraße 5, 01307 Dresden",
        "keys": "Transponder",
        "rules": "Küchennutzung nur bis 21 Uhr",
        "beds_basic": 3,
        "beds_luxury": 1,
        "date_from_june": date(2025, 6, 15),
        "date_to_june": date(2025, 6, 30),
        "latitude": "51.0458",
        "longitude": "13.7766",
        "internal_comment": "WLAN-Ausbau geplant für Mitte Juni",
        "area": "Johannstadt"
    },
    {
        "uuid": str(uuid.uuid4()),
        "name": "Alexander D.",
        "pronoun": "they/them",
        "telephone": "0351 112233",
        "address": "Tiergartenstraße 27, 01219 Dresden",
        "keys": "Digitalschloss",
        "rules": "Rauchverbot im gesamten Haus",
        "beds_basic": 2,
        "beds_luxury": 2,
        "date_from_june": date(2025, 6, 5),
        "date_to_june": date(2025, 6, 25),
        "latitude": "51.0284",
        "longitude": "13.7609",
        "internal_comment": "Ruheraum wird am 14.06. renoviert",
        "area": "Strehlen"
    },
    {
        "uuid": str(uuid.uuid4()),
        "name": "Andreas S.",
        "pronoun": "er/ihn",
        "telephone": "0351 445566",
        "address": "Chemnitzer Straße 85, 01187 Dresden",
        "keys": "Schlüssel für Haupteingang und Zimmer",
        "rules": "Nur für Einzelpersonen, keine Gruppen",
        "beds_basic": 2,
        "beds_luxury": 0,
        "date_from_june": date(2025, 6, 18),
        "date_to_june": date(2025, 6, 30),
        "latitude": "51.0356",
        "longitude": "13.7174",
        "internal_comment": "Notschlafstelle mit ehrenamtlicher Betreuung",
        "area": "Südvorstadt"
    },
    {
        "uuid": str(uuid.uuid4()),
        "name": "Saskia E.",
        "pronoun": "sie/ihr",
        "telephone": "0351 123456",
        "address": "Königsbrücker Straße 43, 01099 Dresden",
        "keys": "Haupteingang, Zimmerschlüssel",
        "rules": "Nachtruhe ab 22 Uhr, keine Haustiere",
        "beds_basic": 4,
        "beds_luxury": 2,
        "date_from_june": date(2025, 6, 23),
        "date_to_june": date(2025, 6, 30),
        "latitude": "51.0651",
        "longitude": "13.7418",
        "internal_comment": "Neue Matratzen am 30. Mai geliefert",
        "area": "Neustadt"
    },
    {
        "uuid": str(uuid.uuid4()),
        "name": "Frank-Walther S.",
        "pronoun": "er/ihn",
        "telephone": "0351 654321",
        "address": "Bautzner Straße 5, 01099 Dresden",
        "keys": "Code für Tür, Schlüssel für Spind",
        "rules": "Kein Alkohol, keine Besucher nach 20 Uhr",
        "beds_basic": 4,
        "beds_luxury": 1,
        "date_from_june": date(2025, 6, 12),
        "date_to_june": date(2025, 6, 18),
        "latitude": "51.0645",
        "longitude": "13.7631",
        "internal_comment": "Tägliche Reinigung durch Externen",
        "area": "Äußere Neustadt"
    },
    {
        "uuid": str(uuid.uuid4()),
        "name": "Markus S.",
        "pronoun": "sie/ihr",
        "telephone": "0351 888888",
        "address": "Pfotenhauerstraße 423, 01307 Dresden",
        "keys": "Transponder",
        "rules": "keine vegane Wurst erlaubt",
        "beds_basic": 3,
        "beds_luxury": 1,
        "date_from_june": date(2025, 6, 15),
        "date_to_june": date(2025, 6, 30),
        "latitude": "51.0458",
        "longitude": "13.7766",
        "internal_comment": "WLAN-Ausbau geplant für Mitte Juni",
        "area": "Johannstadt"
    },
    {
        "uuid": str(uuid.uuid4()),
        "name": "Robert H.",
        "pronoun": "they/them",
        "telephone": "0351 112233",
        "address": "Tiergartenstraße 30, 01219 Dresden",
        "keys": "Digitalschloss",
        "rules": "Rauchverbot im gesamten Haus",
        "beds_basic": 2,
        "beds_luxury": 3,
        "date_from_june": date(2025, 6, 1),
        "date_to_june": date(2025, 6, 6),
        "latitude": "51.0284",
        "longitude": "13.7609",
        "internal_comment": "Ruheraum wird am 14.06. renoviert",
        "area": "Strehlen"
    },
    {
        "uuid": str(uuid.uuid4()),
        "name": "Andrea N.",
        "pronoun": "er/ihn",
        "telephone": "0351 445566",
        "address": "Chemnitzer Straße 84, 01187 Dresden",
        "keys": "Schlüssel für Haupteingang und Zimmer",
        "rules": "You're unfired",
        "beds_basic": 2,
        "beds_luxury": 5,
        "date_from_june": date(2025, 6, 7),
        "date_to_june": date(2025, 6, 23),
        "latitude": "51.0356",
        "longitude": "13.7174",
        "internal_comment": "Notschlafstelle mit ehrenamtlicher Betreuung",
        "area": "Südvorstadt"
    }

]


def random_name() -> str:
    '''generate random names from a set of 100 names and 50 surnames'''
    names = [
    "Anna", "Miguel", "Aisha", "Hiroshi", "Fatima", "Luca", "Sofia", "Jamal", "Yara", "Mateo",
    "Leila", "Nikolai", "Amara", "Omar", "Hana", "Carlos", "Mei", "Ibrahim", "Zoe", "Luis",
    "Anya", "Tariq", "Sinead", "Raj", "Elena", "Mateo", "Nadia", "Kenji", "Amina", "Felix",
    "Imani", "Alexei", "Noor", "Diego", "Kaori", "Selim", "Lina", "Pedro", "Yasmin", "Satoshi",
    "Malika", "Theo", "Alina", "Zain", "Amelie", "Jamila", "Stefan", "Nia", "Rafael", "Daria",
    "Malik", "Freya", "Kofi", "Sara", "Javier", "Laila", "Boris", "Anika", "Samir", "Ingrid",
    "Omar", "Maja", "Hassan", "Elina", "Tarek", "Yasmina", "Elias", "Aaliyah", "Bruno", "Malin",
    "Zofia", "Karim", "Ingrid", "Mateus", "Lila", "Arjun", "Maya", "Sven", "Amira", "Tariq",
    "Sofia", "Rashid", "Maren", "Ibrahim", "Noemi", "Khalid", "Alina", "Luca", "Noura", "Victor",
    "Leila", "Samira", "Emil", "Dalia", "Rajesh", "Selma", "Jonas", "Amina", "Luis", "Hana", 'Uwe']

    surnames = [
    "Müller", "Kumar", "Garcia", "Wang", "Smith", "Ahmed", "Ivanov", "Hernandez", "Tanaka", "Ali",
    "Petrov", "Gonzalez", "Nguyen", "Kowalski", "Dubois", "Silva", "Yamamoto", "Brown", "Schneider", "Rahman",
    "Popescu", "Rodriguez", "Lee", "Bakker", "Singh", "Hussein", "Martinez", "Nakamura", "Öztürk", "Johansson",
    "Novak", "Fernandes", "Meier", "Sato", "Lopez", "Kim", "Kone", "Zimmermann", "Baranov", "Castro",
    "Takahashi", "Weber", "Chowdhury", "Da Silva", "Nowak", "Moreno", "Saidi", "Gruber", "Bakr", "Schmitt"]

    return f'{choice(names)} {choice(surnames)}'


def generate_Mensch_data():    
    bezugi = choice(['Kresse', 'Wilder Rucola', 'Sauerampfer', 'Wütendampfer',
                     'Milder Ampfer', 'Schlauerampfer', 'Angeberampfer'])

    Mensch_dict = {
        'name': random_name(),
        'telephone': f'04663 {randint(100, 99999)}',
        'bezugsgruppe': bezugi,
        'date_from': date(2025, 6, randint(1, 14)),
        'date_to': date(2025, 6, randint(14, 30)),
        'birthday': date(randint(1950, 2009), randint(1, 12), randint(1, 28)),
        'relative': f'{random_name()} (04841 {randint(100, 99999)})',
        'flinta': choice(['Ja', 'Nein']),
        'non_food': 'Erbsen und Wurzeln',
        'needs': 'Love and Support',
        'fellows': ''
    }

    return Mensch_dict

def clear_database():
    meta = db.metadata
    conn = db.engine.connect()

    trans = conn.begin()
    for table in reversed(meta.sorted_tables):
        conn.execute(table.delete())
    trans.commit()
    conn.close()


with app.app_context():
    if 'unterkünfte_test' in settings.DB_LOCATION:
        clear_database()
    for _shelter_data in shelter_data:
        s = Shelter(**_shelter_data)
        db.session.add(s)

    for i in range(30):
        m = Mensch(**generate_Mensch_data())
        db.session.add(m)
    
    db.session.commit()



