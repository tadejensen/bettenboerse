import numpy as np
import pandas as pd
from datetime import timedelta, date
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D                     # neu
from matplotlib.ticker import FuncFormatter
import sqlite3
import io
from flask import Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import re


def read_sqlite(dbfile):
    with sqlite3.connect(dbfile) as dbcon:
        #tables = list(pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", dbcon)['name'])
        tables = ["shelter", "reservation", "mensch"]
        out = {tbl: pd.read_sql_query(f"SELECT * from {tbl}", dbcon) for tbl in tables}
        return out


def format_name(name, linelen=20):
    lines = int(np.ceil(len(name) / linelen))
    charperline = int(len(name) / lines)
    ukname = ""
    for line in range(lines):
        namefitzel = name[line * charperline:(line + 1) * charperline]
        if line != lines - 1:
            namefitzel = namefitzel + "-\n"
        ukname = ukname + namefitzel

    return ukname


def hist_betten(dbfile="unterkünfte.db", start_plot="2022-06-18", end_plot="2022-07-20"):
    a = read_sqlite(dbfile)
    start = pd.to_datetime("2022-06-18")
    end_plot = pd.to_datetime(end_plot)
    start_plot = pd.to_datetime(start_plot)

    betten = pd.DataFrame(a["shelter"])
    menschen = a["mensch"]
    reservations = pd.DataFrame(a["reservation"])

    fig_hist = plt.figure(tight_layout=True, figsize=(13, 7))
    ax_hist = plt.subplot(111)

    bedcounts = []
    menschcounts = []

    t1_max = max(pd.to_datetime(betten["date_to_june"]))

    for i in range((t1_max - start).days):
        day = start + timedelta(days=i)
        valbeds = betten[
            (pd.to_datetime(betten["date_from_june"]) <= day) & (pd.to_datetime(betten["date_to_june"]) > day)]
        valbedcount = np.sum([valbeds["beds_basic"], valbeds["beds_luxury"]])

        valpeople = np.sum((pd.to_datetime(menschen["date_from"]) <= day) & (pd.to_datetime(menschen["date_to"]) > day))

        bedcounts.append((i, valbedcount))
        menschcounts.append((i - .15, valpeople))

    reservations["date"] = pd.to_datetime(reservations["date"])
    resdates = set(reservations["date"])
    resdates_ind = []
    resplaces = []

    for ddate in resdates:
        resdates_ind.append((ddate - start).days)
        reses = reservations[reservations["date"] == ddate]
        date_ind = (ddate - start).days
        for ind in reses.index:
            res = reses.loc[ind]
            rescount = len(reses)
        resplaces.append((date_ind + .15, rescount))

    bedcounts = np.array(bedcounts)
    resplaces = np.array(resplaces)
    menschcounts = np.array(menschcounts)

    ax_hist.bar(bedcounts[:, 0], bedcounts[:, 1], color="lightgreen", zorder=2.11, label="vorhandene Betten", width=.8)
    ax_hist.bar(resplaces[:, 0], resplaces[:, 1], zorder=2.12, color="gold", label="belegte Betten", width=.3)
    ax_hist.bar(menschcounts[:, 0], menschcounts[:, 1], zorder=2.12, color="skyblue", label="Gesuche", width=.3)

    OG_xlim = ax_hist.get_xlim()
    ax_hist.set_xticks(np.arange(0, (t1_max - start).days, 5))
    ax_hist.set_xticks(np.arange(0, (t1_max - start).days, 1), minor=True)

    xticklabs = []
    for tick in ax_hist.get_xticks():
        datei = start + timedelta(days=int(tick))
        xticklabs.append(datei.strftime("%d. (%a)"))

    ax_hist.set_yticks(np.arange(0, np.max(ax_hist.get_yticks()), 5), minor=True)
    ax_hist.yaxis.grid()
    ax_hist.yaxis.grid(which="minor", alpha=.25)

    xlim = ((start_plot - start).days - .5, (end_plot - start).days + .5)

    ax_hist.set(xticklabels=xticklabs, xlim=xlim,
                xlabel="Datum", ylabel="Schlafplätze")
    ax_hist.legend()
    ax_hist.xaxis.set_tick_params(rotation=45)

    ax_hist.xaxis.set_minor_formatter(FuncFormatter(int_to_date))

    today = pd.to_datetime(date.today())
    ax_hist.axvline((today - start).days - .2, zorder=3, ls="--", color="red")

    output = io.BytesIO()
    FigureCanvas(fig_hist).print_png(output)
    return Response(output.getvalue(), mimetype="image/png")


def int_to_date(value, pos):
    start = pd.to_datetime("2022-06-18")
    ddate = start + timedelta(days=int(value))
    return ddate.strftime("%a")


def plot_calendar(dbfile="unterkünfte.db", start_plot="2022-06-18", end_plot="2022-07-20"):
    """
    dbfile: str zu unterkuefte.db
    start_date: str im Format 'yyyy-mm-dd'
        linke Anzeigegrenze des Plots
    end_date:

    """

    a = read_sqlite(dbfile)
    start = pd.to_datetime("2022-06-18")
    end_plot = pd.to_datetime(end_plot)
    start_plot = pd.to_datetime(start_plot)

    betten = pd.DataFrame(a["shelter"])
    reservations = pd.DataFrame(a["reservation"])
    # reshuman = pd.DataFrame(a["reservations_mensch"])
    # humans = pd.DataFrame(a["menschen"])

    height = 1
    legend_elements = [Patch(facecolor="lightgreen", edgecolor="none", label="frei Isomatte"),
                       Patch(facecolor="tab:green", edgecolor="none", label="frei Bett"),
                       Patch(facecolor="lightcoral", edgecolor="none", label="belegt"),
                       Line2D([0], [0], ls="dashed", color="red", label="heute")]

    fig_cal = plt.figure(tight_layout=True, figsize=(13, 8))
    ax_cal = plt.subplot()

    k = 0
    t1_max = pd.to_datetime("2022-06-18")

    yticks = []
    yticklabs = []

    for ind in betten.index:
        unterkunft = betten.loc[ind]
        ax_cal.axhline(k, ls="dashed", color="grey", lw=.75)
        k += .4 * height
        bed = unterkunft["beds_luxury"]
        iso = unterkunft["beds_basic"]
        ukname = format_name(unterkunft["name"])
        yticklabs.append(f'{ukname} ({bed + iso})')
        yticks.append(k + (bed + iso) / 2)

        t0 = pd.to_datetime(unterkunft["date_from_june"])
        t1 = pd.to_datetime(unterkunft["date_to_june"])

        if t1 is None:
            print(f"Unterkunft von {unterkunft['name']} hat kein Enddatum angegeben. 2. Juli angenommen.")
            t1 = pd.to_datetime("2022-07-02")

        t1_max = max(t1, t1_max)

        if unterkunft["uuid"] in list(reservations["shelter_id"]):
            reses = reservations[reservations["shelter_id"] == unterkunft["uuid"]]
            datecounts = reses.date.value_counts()
            for resdate in datecounts.index:
                datecount = datecounts.loc[resdate]
                resdate = pd.to_datetime(resdate)
                resdate_ind = (resdate - start).days

                ax_cal.add_patch(Rectangle((resdate_ind + .5, k), 1, datecount * height,
                                           facecolor="lightcoral", edgecolor="none", zorder=3))

        for bedi in range(bed):
            ax_cal.add_patch(Rectangle(((t0 - start).days + .5, k), (t1 - t0).days, height, facecolor="tab:green",
                                       edgecolor="none", zorder=2))
            ax_cal.add_patch(Rectangle(((t0 - start).days + .5, k), (t1 - t0).days, height, facecolor="none",
                                       edgecolor="grey", lw=.5, zorder=3.5))
            k += height
        for isoi in range(iso):
            ax_cal.add_patch(Rectangle(((t0 - start).days + .5, k), (t1 - t0).days, height, facecolor="lightgreen",
                                       edgecolor="none", zorder=2))
            ax_cal.add_patch(Rectangle(((t0 - start).days + .5, k), (t1 - t0).days, height, facecolor="none",
                                       edgecolor="grey", lw=.5, zorder=3.5))
            k += height

        k += .4 * height

    fig_cal.set_size_inches(13, k * .075)

    ax_cal.legend(handles=legend_elements)
    ax_cal.xaxis.grid(zorder=1)
    ax_cal.set(xlim=((start_plot - start).days - 1, (end_plot - start).days + 1), ylim=(0, k + .5),
               xlabel="Datum",
               yticks=yticks, yticklabels=yticklabs)

    ax_cal.set_xticks(np.arange(0, (t1_max - start).days, 5))
    ax_cal.set_xticks(np.arange((t1_max - start).days), minor=True)
    ax_cal.xaxis.grid(which="minor", zorder=1, alpha=.25)

    ax_cal.xaxis.set_major_formatter(FuncFormatter(int_to_date_maj))
    ax_cal.xaxis.set_minor_formatter(FuncFormatter(int_to_date))

    ax_cal.xaxis.set_tick_params(rotation=90, which="both")
    ax_cal.set(xlim=((start_plot - start).days - 1, (end_plot - start).days + 1),
               ylim=(.001, k + .5))

    today = pd.to_datetime(date.today())
    ax_cal.axvline((today - start).days + .35, color="red", ls="--", zorder=4)
    output = io.BytesIO()
    FigureCanvas(fig_cal).print_png(output)
    return Response(output.getvalue(), mimetype="image/png")


def int_to_date_maj(value, pos):
    start = pd.to_datetime("2022-06-18")
    ddate = start + timedelta(days=int(value))
    return ddate.strftime("%d. (%a)")


def plot_menschen(dbfile="unterkünfte.db", start_plot="2022-06-17", end_plot="2022-07-20", today=None):
    """
    dbfile: str zu unterkuefte.db
    start_date: str im Format 'yyyy-mm-dd'
        linke Anzeigegrenze des Plots
    end_date:

    """
    a = read_sqlite(dbfile)
    start = pd.to_datetime("2022-06-18")
    try:
        end_plot = pd.to_datetime(end_plot)
    except:
        print("Als Enddatum fürs Plotten wird längster Aufenthalt genommen")
    start_plot = pd.to_datetime(start_plot)

    height = 1

    betten = pd.DataFrame(a["shelter"])
    reservations = pd.DataFrame(a["reservation"])
    menschen = a["mensch"]

    legend_elements = [Patch(facecolor="gold", edgecolor="none", label="untergebracht"),
                       Patch(facecolor="skyblue", edgecolor="none", label="in Berlin"),
                       Line2D([0], [0], ls="dashed", color="red", label="heute"),
                       Line2D([0], [0], color="gray", label="Umzug")]

    menschen = menschen.sort_values("bezugsgruppe", ascending=False)

    fig = plt.figure(tight_layout=True, figsize=(13, 8))
    ax = plt.subplot(111)

    yticks = []
    ylabs = []
    k = 0

    tmax = pd.to_datetime(menschen["date_to"]).max()

    for ind in menschen.index:
        mensch = menschen.loc[ind]
        start_mensch = (pd.to_datetime(mensch["date_from"]) - start).days
        end_mensch = (pd.to_datetime(mensch["date_to"]) - start).days
        span = end_mensch - start_mensch
        name = mensch["name"]
        bg = re.split(r"\W+", mensch["bezugsgruppe"])[0]
        if bg.capitalize() == "Wilder":
            bg = "Wilder Rucola"
        ylabs.append(f'{name} ({bg})')
        yticks.append(k + height / 2)
        ax.add_patch(Rectangle((start_mensch + .5, k), span, height, facecolor="skyblue", edgecolor="none", zorder=.5))

        res_mensch = reservations[reservations["mensch_id"] == mensch["id"]]
        for res_ind in res_mensch.index:
            res = res_mensch.loc[res_ind]
            resdate = pd.to_datetime(res["date"])
            resdate_next = str(resdate + timedelta(days=1))[:10]
            date_int = (resdate - start).days

            there_tomorrow = res_mensch["date"].str.contains(resdate_next).any()
            same_shelter_tomorrow = (res_mensch[res_mensch["date"] == resdate_next]["shelter_id"] == res[
                "shelter_id"]).sum()
            if (not same_shelter_tomorrow) & there_tomorrow:
                ax.vlines(date_int + 1.65, ymin=k, ymax=k + height, color="grey")

            ax.add_patch(
                Rectangle((date_int + .5, k + .15 * height), 1, height * .7, edgecolor="none", facecolor="gold"))

        k += 1.1 * height

    fig.set_size_inches(13, k * .15)

    minticks = np.arange(-1, (tmax - start).days + 2, 1)
    majticks = np.arange(0, (tmax - start).days + 2, 5)

    ax.set_xticks(minticks, minor=True)
    ax.set_xticks(majticks)

    ax.xaxis.set_minor_formatter(FuncFormatter(int_to_date))
    ax.xaxis.set_major_formatter(FuncFormatter(int_to_date_maj))

    ax.xaxis.grid(which="major", zorder=2.1)
    ax.xaxis.grid(which="minor", zorder=2.1, alpha=.25)

    if not today:
        today = pd.to_datetime(date.today())
    ax.axvline((today - start).days + .35, color="red", ls="dashed")

    if end_plot:
        tmax = end_plot
    ax.set(xlim=((pd.to_datetime(start_plot) - start).days, (tmax - start).days + 1),
           ylim=(-.25 * height, k + .25 * height), yticks=yticks, yticklabels=ylabs,
           xlabel="Datum")

    ax.xaxis.set_tick_params(rotation=90)

    ax.legend(handles=legend_elements)

    # plt.savefig("menschen.png")

    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype="image/png")
