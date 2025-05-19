import numpy as np
from datetime import timedelta, date
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.dates as mdates
from sqlalchemy.sql import func
from sqlalchemy import desc
import io
from flask import Response

from datetime import date

import settings
from bettenboerse.models import Shelter, Reservation, Mensch

def format_name(name: str, linelen: int=20) -> str:
    '''inserts linebreaks into names that are longer than a given number of
    characters'''
    lines = int(np.ceil(len(name) / linelen))
    charperline = int(len(name) / lines)
    ukname = ""
    for line in range(lines):
        namefitzel = name[line * charperline:(line + 1) * charperline]
        if line != lines - 1:
            namefitzel = namefitzel + "-\n"
        ukname = ukname + namefitzel

    return ukname

def add_today_vline(ax):
    '''adds a vertical red dashed line into ax, at today's date.'''
    if (today:= date.today()) > settings.start_date-timedelta(days=7)\
            and today < settings.end_date+timedelta(days=7):
        ax.axvline(today, zorder=3, ls="--", color="red", label='Heute')

def plot_date_rectangle(ax, start_date: date, end_date: date,
                        height: float, start_y: float, hour_offset: int=12,
                        **kwargs):
    '''
    Plot a rectanlge ranging over a span of dates.
    start/end date: representing x-span of rectangle
    height: height of rectangle
    start_y: lower boundry of rectangle
    offset_hours: int/float, default 12. x axis offset in hours (positive -> 
        move to the right)
    kwargs are passed to ax.add_patch
    '''
    rectangle_xy = (mdates.date2num(start_date + timedelta(hours=hour_offset)),
                    start_y)
    rectangle_width = (end_date - start_date).days
    ax.add_patch(Rectangle(rectangle_xy, rectangle_width, height, **kwargs))


def barplot_beds(app):
    '''
    create a barplot showing available beds, people in need and reservations
    by day.
    '''
    start = settings.start_date
    end = settings.end_date

    with app.app_context():
        shelters = (Shelter.query
                .filter(Shelter.date_to_june >= settings.start_date,
                        Shelter.date_from_june < settings.end_date))
        menschen = (Mensch.query
                    .filter(Mensch.date_to >= settings.start_date,
                            Mensch.date_from < settings.end_date))
        reservations = (Reservation.query
                        .filter(Reservation.date >= settings.start_date,
                                Reservation.date < settings.end_date))
        
        bedcounts = {} # {day_from_start: available_beds_counter, ...}
        menschcounts = {} # {day_from_start: peole_in_need_counter, ...}
        reservationcounts = {}


        for i in range((end - start).days):
            day = start + timedelta(days=i)

            available_beds = shelters.filter(Shelter.date_from_june <= day,
                                        Shelter.date_to_june > day)
            needy_people = menschen.filter(Mensch.date_from <= day,
                                        Mensch.date_to > day)
            _reservations = reservations.filter(Reservation.date == day)

            bedcounts[day] = sum([s.beds_total for s in available_beds.all()])
            menschcounts[day-timedelta(hours=5)] = len(needy_people.all())        # small offset for visualization
            reservationcounts[day+timedelta(hours=5)] = len(_reservations.all())

    fig, ax = plt.subplots(figsize=(13, 7), layout='constrained')

    ax.bar(bedcounts.keys(), bedcounts.values(), 
           color="lightgreen", zorder=2.11, label="Verfügbare Betten", width=.8)
    ax.bar(reservationcounts.keys(), reservationcounts.values(),
           zorder=2.12, color="gold", label="Verteilte Menschen", width=.3,
           align='edge')
    ax.bar(menschcounts.keys(), menschcounts.values(),
           zorder=2.12, color="skyblue", label="Gesuche", width=-.3, align='edge')

    ax.set(xlabel="Datum", ylabel="Schlafplätze")
    ax.legend()
    ax.xaxis.set_tick_params(rotation=45)

    add_today_vline(ax)
    ax.grid(visible=True, axis='y', zorder=1)

    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype="image/png")


def plot_calendar(app):
    """
    Create a timeline of avalable shelters.
    Green blocks represent the shelters, red blocks represent the reservations 
    made to the shelter.
    """
    rowheight = 1
    start = settings.start_date
    end = settings.end_date

    def plot_shelterblock(ax, start_date, end_date, spot_counter, start_y, color):
        # plot background block for beds, without framing
        plot_date_rectangle(ax, start_date, end_date, rowheight*spot_counter,
                            start_y, facecolor=color, edgecolor='none', zorder=2)
        for spot in range(spot_counter):
            # frame that sits on top of the red reservation marker
            plot_date_rectangle(ax, start_date, end_date, rowheight,
                                start_y+spot * rowheight,
                                facecolor='none', edgecolor='grey',
                                lw=0.5, zorder=3.5)

    legend_elements = [Patch(facecolor="lightgreen", edgecolor="none", label="frei Isomatte"),
                       Patch(facecolor="tab:green", edgecolor="none", label="frei Bett"),
                       Patch(facecolor="lightcoral", edgecolor="none", label="belegt"),
                       Line2D([0], [0], ls="dashed", color="red", label="heute")]

    fig_cal = plt.figure(figsize=(13, 8), layout='constrained')
    ax_cal = plt.subplot()

    height_current_stack = 0

    yticks = []
    yticklabs = []


    with app.app_context():
        shelters = (Shelter.query
                .filter(Shelter.date_to_june >= settings.start_date,
                        Shelter.date_from_june < settings.end_date)
                .order_by(desc(Shelter.date_from_june),
                          desc(func.julianday(Shelter.date_to_june) \
                                    - func.julianday(Shelter.date_from_june))))

        reservations = (Reservation.query
                        .filter(Reservation.date >= settings.start_date,
                                Reservation.date < settings.end_date))
        for shelter in shelters.all():
            # gather data for green block (represents the shelter)
            ax_cal.axhline(height_current_stack, ls="dashed", color="grey", lw=.75)
            height_current_stack += .4 * rowheight

            n_beds = shelter.beds_luxury
            n_basic = shelter.beds_basic
            
            sheltername = format_name(shelter.name)

            yticklabs.append(f'{sheltername} ({n_beds + n_basic})')
            yticks.append(height_current_stack + (n_beds + n_basic) / 2)

            t0 = shelter.date_from_june

            if (t1 := shelter.date_to_june) is None:
                t1 = end
                print(f"Unterkunft {sheltername} hat kein Enddatum angegeben. {t1} angenommen.")

            # fill reservations (red) into green block
            res_this_shelter = reservations.filter(Reservation.shelter_id == shelter.uuid)
            date_counter = (res_this_shelter.order_by(Reservation.date)
                            .with_entities(Reservation.date, 
                                           func.count(Reservation.date))
                            .group_by(Reservation.date).all())
            for date, counter in date_counter:
                plot_date_rectangle(ax_cal, date, date+timedelta(days=1),
                                    counter*rowheight, height_current_stack, 
                                    facecolor="lightcoral", edgecolor="none",
                                    zorder=3)

            # plot green block for beds aand basic sleeping spots
            for spot_counter, color in [(n_beds, 'tab:green'),
                                        (n_basic, 'lightgreen')]:
                plot_shelterblock(ax_cal, t0, t1, spot_counter, height_current_stack, color)
                height_current_stack += rowheight * spot_counter

            height_current_stack += .4 * rowheight

    fig_cal.set_size_inches(13, 1 + height_current_stack * .075)

    ax_cal.legend(handles=legend_elements)
    ax_cal.xaxis.grid(zorder=1)
    ax_cal.set(xlim=(start - timedelta(days=2), end + timedelta(days=1)),
               ylim=(.001, height_current_stack + .5),
               xlabel="Datum",
               yticks=yticks, yticklabels=yticklabs)

    ax_cal.xaxis.grid(which="minor", zorder=1, alpha=.25)
    ax_cal.xaxis.set_tick_params(rotation=90, which="both")

    add_today_vline(ax_cal)

    # fig_cal.savefig(r'C:\Users\tadej\Documents\Programmierkrams\Bettenboerse\calendar.png')

    output = io.BytesIO()
    FigureCanvas(fig_cal).print_png(output)
    return Response(output.getvalue(), mimetype="image/png")


def plot_menschen(app):
    """
    Create a timeline-like graph of Menschen in database, showing
        1. when they are there
        2. if/when they have a reservation
        3. if/when they move
    """
    start = settings.start_date
    end = settings.end_date

    with app.app_context():
        menschen = (Mensch.query
                    .filter(Mensch.date_to >= settings.start_date,
                            Mensch.date_from < settings.end_date)
                    .order_by(Mensch.bezugsgruppe, Mensch.date_from))
        reservations = (Reservation.query
                        .filter(Reservation.date >= settings.start_date,
                                Reservation.date < settings.end_date))

        height = 1

        legend_elements = [Patch(facecolor="gold", edgecolor="none", label="untergebracht"),
                        Patch(facecolor="skyblue", edgecolor="none", label="vor Ort"),
                        Line2D([0], [0], ls="dashed", color="red", label="heute"),
                        Line2D([0], [0], color="gray", label="Umzug")]

        fig = plt.figure(figsize=(13, 8), layout='constrained')
        ax = plt.subplot(111)

        yticks = []
        ylabs = []
        height_current_stack = 0.6

        for mensch in menschen.all():
            mensch_start = mensch.date_from
            mensch_end = mensch.date_to
            name = mensch.name            
            bezugi = mensch.bezugsgruppe

            ylabs.append(f'{name} ({bezugi})')
            yticks.append(height_current_stack + height / 2)

            # plot blue rectangle representing the person's entire stay
            plot_date_rectangle(ax, mensch_start, mensch_end, height,
                                height_current_stack, facecolor="skyblue",
                                edgecolor="none", zorder=2)
            
            
            res_mensch = reservations.filter(Reservation.mensch_id == mensch.id)

            # add reservations to the plot, mark moves as grey vline
            old_shelter_id = None
            for single_res in res_mensch.order_by(Reservation.date).all():
                resdate = single_res.date
                date_tomorrow = resdate + timedelta(days=1)
                shelter_id = single_res.shelter_id

                # gold rectangle for bed managing done
                plot_date_rectangle(ax, resdate, date_tomorrow, height * .7,
                                    height_current_stack + .15 * height,
                                    edgecolor="none", facecolor="gold",
                                    zorder=2.5)
                
                # grey line for move
                if (old_shelter_id is not None) and (shelter_id != old_shelter_id):
                    ax.vlines(resdate - timedelta(hours=12),
                              ymin=height_current_stack, ymax=height_current_stack + height,
                              color="grey", zorder=3)
                    
                old_shelter_id = shelter_id

            height_current_stack += 1.1 * height

    fig.set_size_inches(13, 1 + height_current_stack * .15)

    ax.set(xlim=(start - timedelta(days=2), end + timedelta(days=1)),
           ylim=(0.001, height_current_stack + .25 * height),
           yticks=yticks,
           yticklabels=ylabs,
           xlabel='Datum')
    ax.grid(visible=True, which="major", axis='x', zorder=1)
    ax.grid(visible=True, which="minor",axis='x', zorder=1, alpha=.25)

    add_today_vline(ax)

    ax.xaxis.set_tick_params(rotation=90)
    ax.legend(handles=legend_elements)

    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype="image/png")


