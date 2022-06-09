from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, column_property

db = SQLAlchemy()


class Shelter(db.Model):
    __tablename__ = 'shelter'

    uuid = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(100))
    pronoun = db.Column(db.String(100))
    telephone = db.Column(db.String(100))
    address = db.Column(db.String())
    keys = db.Column(db.String())
    rules = db.Column(db.String())
    beds_basic = db.Column(db.Integer)
    beds_luxury = db.Column(db.Integer)
    date_from_june = db.Column(db.Date())
    date_to_june = db.Column(db.Date())
    latitude = db.Column(db.String())
    longitude = db.Column(db.String())
    # TODO: rename lg_comment to internal_comment
    lg_comment = db.Column(db.String())
    menschen = relationship("Reservation", back_populates="shelter")
    beds_total = column_property(beds_basic + beds_luxury)

    #def get_reservations_by_date(self, date):
    #    reservations = {}
    #    for reservation in self.menschen:
    #        reservations[reservation.date] = reservation
    #    return reservations


class Reservation(db.Model):
    __tablename__ = "reservation"
    shelter_id = db.Column(db.ForeignKey("shelter.uuid"), primary_key=True)
    mensch_id = db.Column(db.ForeignKey("mensch.id"), primary_key=True)
    date = db.Column(db.Date(), primary_key=True)
    mensch = relationship("Mensch", back_populates="shelters")
    shelter = relationship("Shelter", back_populates="menschen")


class Mensch(db.Model):
    __tablename__ = "mensch"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    shelters = relationship("Reservation", back_populates="mensch")
    telephone = db.Column(db.String())
    bezugsgruppe = db.Column(db.String())


#import enum
#class ReservationState(enum.Enum):
#    FREE = 'green', 'alle Plätze frei'
#    PARTIAL = 'orange', 'teilweise belegt'
#    FULL = 'red', 'alle Plätze belegt'
