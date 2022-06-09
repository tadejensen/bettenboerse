from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

db = SQLAlchemy()


#class SleepingPlace(db.Model):
#    __tablename__ = 'sleeping_places'
#
#    uuid = db.Column(db.String(100), primary_key=True)
#    name = db.Column(db.String(100))
#    pronoun = db.Column(db.String(100))
#    telephone = db.Column(db.String(100))
#    address = db.Column(db.String())
#    keys = db.Column(db.String())
#    rules = db.Column(db.String())
#    sleeping_places_basic = db.Column(db.Integer)
#    sleeping_places_luxury = db.Column(db.Integer)
#    date_from_june = db.Column(db.Date())
#    date_to_june = db.Column(db.Date())
#    latitude = db.Column(db.String())
#    longitude = db.Column(db.String())
#    lg_comment = db.Column(db.String())

class Shelter(db.Model):
    __tablename__ = 'shelter'

    uuid = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(100))
    pronoun = db.Column(db.String(100))
    telephone = db.Column(db.String(100))
    address = db.Column(db.String())
    keys = db.Column(db.String())
    rules = db.Column(db.String())
    sleeping_places_basic = db.Column(db.Integer)
    sleeping_places_luxury = db.Column(db.Integer)
    date_from_june = db.Column(db.Date())
    date_to_june = db.Column(db.Date())
    latitude = db.Column(db.String())
    longitude = db.Column(db.String())
    # TODO: rename lg_comment to internal_comment
    lg_comment = db.Column(db.String())
    menschen = relationship("Reservation2", back_populates="shelter")


#class Mensch(db.Model):
#    __tablename__ = 'menschen'
#    id = db.Column(db.Integer, primary_key=True)
#    name = db.Column(db.String())
#    telephone = db.Column(db.String())
#    bezugsgruppe = db.Column(db.String())


#class Reservation(db.Model):
#    __tablename__ = 'reservations'
#
#    id = db.Column(db.Integer, primary_key=True)
#    sleeping_place = db.Column(db.String(100), db.ForeignKey(
#        'sleeping_places.uuid'))
#    date = db.Column(db.Date())
#    #__table_args__ = (UniqueConstraint('sleeping_place', 'date', name='uniq_reservation_per_day'),)
#    #state = db.Column(db.Enum(ReservationState))


#class ReservationMensch(db.Model):
#    __tablename__ = 'reservations_mensch'
#    mensch = db.Column(db.Integer, db.ForeignKey('menschen.id'), primary_key=True)
#    reservation = db.Column(db.Integer, db.ForeignKey('reservations.id'))



class Reservation2(db.Model):
    __tablename__ = "reservations2"
    shelter_id = db.Column(db.ForeignKey("shelter.uuid"), primary_key=True)
    mensch_id = db.Column(db.ForeignKey("mensch.id"), primary_key=True)
    date = db.Column(db.String(50))
    mensch = relationship("Mensch", back_populates="shelters")
    shelter = relationship("Shelter", back_populates="menschen")


#class Shelter(db.Model):
#    __tablename__ = "shelter"
#    id = db.Column(db.Integer, primary_key=True)
#    address = db.Column(db.String)
#    menschen = relationship("Reservation2", back_populates="shelter")


class Mensch(db.Model):
    __tablename__ = "mensch"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    shelters = relationship("Reservation2", back_populates="mensch")
    telephone = db.Column(db.String())
    bezugsgruppe = db.Column(db.String())











import enum
class ReservationState(enum.Enum):
    FREE = 'green', 'alle Plätze frei'
    PARTIAL = 'orange', 'teilweise belegt'
    FULL = 'red', 'alle Plätze belegt'

