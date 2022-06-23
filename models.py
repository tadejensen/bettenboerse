from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, column_property
import datetime
import settings

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
    internal_comment = db.Column(db.String())
    area = db.Column(db.String())
    menschen = relationship("Reservation", back_populates="shelter")
    beds_total = column_property(beds_basic + beds_luxury)

    def __repr__(self):
        #return f"{self.name} ({self.date_from_june} {self.date_to_june})"
        return f"{self.name} {self.beds_total}"

    def get_capacity_by_date(self, date):
        capacity = {}
        reservations = Reservation.query.filter_by(shelter=self).filter_by(date=date).all()
        capacity = {'beds_total': self.beds_total,
                    'beds_used': len(reservations),
                    'beds_free': self.beds_total - len(reservations),
                   }
        return capacity


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
    date_from = db.Column(db.Date())
    date_to = db.Column(db.Date())
    birthday = db.Column(db.Date())
    relative = db.Column(db.String())
    flinta = db.Column(db.String())
    non_food = db.Column(db.String())
    needs = db.Column(db.String())
    fellows = db.Column(db.String())

    def get_last_reservation_date(self):
        last_reservation = Reservation.query.filter_by(mensch_id=self.id).order_by(Reservation.date.desc()).first()
        return last_reservation.date.strftime("%d.%m.") if last_reservation else "keine Reservierung"

    def get_reservation_state(self):
        stay_days = (self.date_to - self.date_from).days
        reservations = Reservation.query.filter_by(mensch=self).count()
        return f"{reservations}/{stay_days}"

    def get_last_message_sent(self):
        #last_message = SignalLog.query.filter_by(mensch=self).filter_by(error=0).order_by(SignalLog.created.desc()).first()
        last_message = SignalLog.query.filter_by(mensch=self).order_by(SignalLog.created.desc()).first()
        return last_message.created.strftime("%d.%m. (%a)") if last_message else "keine Nachricht"


class SignalLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    telephone = db.Column(db.String())
    message = db.Column(db.String())
    # status (0: no error, 1 error)
    status = db.Column(db.Integer)
    error = db.Column(db.String())
    tag = db.Column(db.String())
    mensch_id = db.Column(db.ForeignKey("mensch.id"))
    mensch = relationship("Mensch")


#import enum
#class ReservationState(enum.Enum):
#    FREE = 'green', 'alle Plätze frei'
#    PARTIAL = 'orange', 'teilweise belegt'
#    FULL = 'red', 'alle Plätze belegt'
