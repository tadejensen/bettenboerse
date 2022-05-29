import enum


class ReservationState(enum.Enum):
    FREE = 'green', 'alle Plätze frei'
    PARTIAL = 'orange', 'teilweise belegt'
    FULL = 'red', 'alle Plätze belegt'

