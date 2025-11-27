import logging
import os
import pathlib
from datetime import datetime, timedelta
from pprint import pprint as print
from tempfile import gettempdir

from django.contrib import messages
from django.db.models import Q
from django.http import (
    FileResponse,
    Http404,
    HttpResponseRedirect,
    JsonResponse,
    HttpResponse,
)
from django.shortcuts import redirect, render
from django.urls import reverse

import pandas as pd
from apps.dashboard.models import chatReferenceQuestion
from sp_ask_school import (
    find_school_by_operator_suffix,
    find_school_by_queue_or_profile_name,
)
from apps.dashboard.utils.utils import (
    Chats,
    check_if_Ended_is_none,
    find_chats_for_this_current_hour,
    find_total_chat_for_this_current_hour_that_this_operator_had_picked_up,
    get_chat_duration,
    get_chat_wait,
    get_lh3_client_connection,
    get_protocol_icon,
    get_this_shift_time,
    get_url,
    operator_is_not_none,
    soft_anonimyzation,
)
from apps.dashboard.views.queries.q_homepage import query_for_homepage_recent_chats
from dateutil.parser import parse
from dotenv import dotenv_values
from lh3.api import *
from core.settings.base import BASE_DIR
from django.contrib.auth.decorators import login_required
import time

# This retrieves a Python logging instance (or creates it)
logger = logging.getLogger(__name__)
import os.path


from django.contrib.auth.views import LoginView
from django.shortcuts import redirect


class CustomAdminLoginView(LoginView):
    template_name = "admin/login.html"

    def get_success_url(self):
        # Redirect to homepage (/) after successful admin login
        return "/"


@login_required
def check_cron_job(request, *args, **kwargs):
    ts = datetime.now().strftime(" - %m/%d/%Y, %H:%M:%S")
    filename = "hello.txt"
    # filepath = os.path.join("/usr/src/app/sp_dashboard/tmp_file/", filename)
    filepath = str(pathlib.PurePath("tmp_file", filename))

    with open(filepath, "a") as dumbfile:
        dumbfile.write("</br>hello.txt" + str(ts))

    file_content = []
    with open(filepath, "r") as reader:
        for line in reader.readlines():
            file_content.append("</br>" + line + str(ts))

    return HttpResponse(file_content)


def chat_usage_per_month_for_a_past_year(client, a_given_year):
    """Return totel chats per month

    Args:
        client Client: LH3 API
        a_given_year Int: a year value  (i.e. 2021)

    Returns:
        dict: list of key values
    """
    chats_report = client.chats()
    chats_for_that_time = chats_report.list_year(a_given_year)
    chats_for_that_time = [
        {
            "year": parse(chat.get("date")).year,
            "month": parse(chat.get("date")),
            "month_name": parse(chat.get("date")).strftime("%b"),
            "date": chat.get("date"),
            "count": chat.get("count"),
        }
        for chat in chats_for_that_time
    ]
    # stock last academic year in sessions (if session ACADEMIC do this... )

    given_year_usage_per_month = list()
    for element in range(1, 13):
        this_month = [
            item.get("count", 0)
            for item in chats_for_that_time
            if item.get("month").month == element
        ]
        given_year_usage_per_month.append(sum(this_month))
    return given_year_usage_per_month


@login_required
def get_homepage(request, *args, **kwargs):
    """Homepage of the Ask A Librarian Dashboard

    Args:
        request Request: HTTP Request header

    Returns:
        dict: returns
                - chats of the last 3 days
                - total operator online
                - last year and this year value (i.e. 2022 and 2021)
                - Chat service (queue) availability
    """

    logger.info("Homepage has been accessed")

    today = datetime.today()

    client = get_lh3_client_connection()
    if client == False:
        return HttpResponseRedirect(reverse("lh3_connection_error"))

    number_of_days = 3
    chats = None
    while chats == None:
        chats = query_for_homepage_recent_chats(client, today, number_of_days)
        number_of_days += 1

    chats = soft_anonimyzation(chats)
    chats = [Chats(chat) for chat in chats]

    """
    if request.session.get('last_year_chats_per_month'):
        chats_last_year_per_month=request.session['last_year_chats_per_month']
    else:
        chats_last_year_per_month = chat_usage_per_month_for_a_past_year(client, today.year-1)
        request.session['last_year_chats_per_month'] = chats_last_year_per_month
    """

    client.set_options(version="v1")
    users = client.all("users").get_list()
    users = [user for user in users if user.get("show") != "unavailable"]

    # messages.warning(request, 'Testing messages')

    # Serivces opened
    queues = client.all("queues").get_list()

    # SMS
    all_sms = [qu for qu in queues if "-txt" in qu["name"]]
    sms_available = [texto["name"] for texto in all_sms if texto["show"] == "available"]
    # print("{0}/{1}".format(len(sms_available), len(all_sms)))
    sms_unavailable = [
        texto["name"] for texto in all_sms if texto["show"] == "unavailable"
    ]
    sms_service = (
        "<em>SMS:</em> at least <i>{0} queues opened out of </i> <b> {1}</b>".format(
            len(all_sms) - len(sms_unavailable), len(all_sms)
        )
    )

    # WEB
    without_sms = [qu for qu in queues if "-txt" not in qu["name"]]
    web = [qu for qu in without_sms if "-fr" not in qu["name"]]
    web_unavailable = [
        unavailable["name"]
        for unavailable in web
        if unavailable["show"] == "unavailable"
    ]
    # print("Web service  {0}/{1}".format(len(web) - len(web_unavailable), len(web)))
    web_service = (
        "<em>Web:</em> at least <i>{0} queues opened out of </i> <b> {1}</b>".format(
            len(web) - len(web_unavailable), len(web)
        )
    )

    # FR
    all_fr = [qu for qu in queues if "-fr" in qu["name"]]
    fr_available = [
        fr_chat["name"] for fr_chat in all_fr if fr_chat["show"] == "available"
    ]
    fr_unavailable = [
        unavailable["name"]
        for unavailable in all_fr
        if unavailable["show"] == "unavailable"
    ]
    fr_service = (
        "<em>FR:</em> at least <i>{0} queues opened out of </i> <b> {1}</b>".format(
            len(all_fr) - len(fr_unavailable), len(all_fr)
        )
    )

    # ref_questions = chatReferenceQuestion.objects.filter(started_date__gte='2022-12-11', started_date__lte='2022-12-13').values_list('lh3ChatID', flat=True)
    try:
        ref_questions = chatReferenceQuestion.objects.filter(
            started_date__range=["2022-09-11", "2022-09-12"]
        )
    except:
        ref_questions = None

    this_shift_time = get_this_shift_time()
    return render(
        request,
        "homepage.html",
        {
            "object_list": chats,
            "total_operator_online": users,
            "last_year": today.year - 1,
            "this_year": today.year,
            "sms_service": sms_service,
            "web_service": web_service,
            "fr_service": fr_service,
            "ref_questions": ref_questions,
            "get_this_shift_time": this_shift_time,
        },
    )


@login_required
def download_list_of_chats_on_homepage(request):
    """Download a list of chats

    Args:
        request Request: HTTP Request header

    Returns:
        File: MS Excel file
    """

    today = datetime.today()
    last2Days = today - timedelta(days=2)

    client = get_lh3_client_connection()
    if client == False:
        return HttpResponseRedirect(reverse("lh3_connection_error"))

    chats = client.chats()
    to_date = (
        str(today.year) + "-" + "{:02d}".format(today.month) + "-" + str(today.day)
    )
    chats = chats.list_day(
        year=last2Days.year, month=last2Days.month, day=last2Days.day, to=to_date
    )

    chats = soft_anonimyzation(chats)
    df = pd.DataFrame(chats)
    del df["tags"]
    del df["referrer"]
    del df["id"]
    del df["profile"]
    df["school_from_operator_username"] = df["operator"].apply(
        lambda x: find_school_by_operator_suffix(x)
    )
    df["school_from_queue_name"] = df["queue"].apply(
        lambda x: find_school_by_queue_or_profile_name(x)
    )
    df["guest"] = df["guest"].apply(lambda x: x.split("@")[0][0:8])

    today = datetime.today().strftime("%Y-%m-%d-%H:%M")

    tmp = os.path.join(gettempdir(), ".{}".format(hash(os.times())))
    os.makedirs(tmp)

    filename = "list_of_chats_from_homepage_" + today + ".xlsx"
    filepath = str(pathlib.PurePath(tmp, filename))

    writer = pd.ExcelWriter(filepath, engine="xlsxwriter")
    df.to_excel(writer, index=False)
    writer.save()

    return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)


@login_required
def service_web(request):
    """return the availability or unavailability of a chat service

    Args:
        request Request: HTTP Request header

    Returns:
        JSON['service']: available or unavailable
    """
    service = get_url("scholars-portal")
    return JsonResponse({"service": service}, safe=False)


@login_required
def service_sms(request):
    """return the availability or unavailability of a chat service

    Args:
        request Request: HTTP Request header

    Returns:
        JSON['service']: available or unavailable
    """
    service = get_url("scholars-portal-txt")
    return JsonResponse({"service": service}, safe=False)


@login_required
def service_fr(request):
    """return the availability or unavailability of a chat service

    Args:
        request Request: HTTP Request header

    Returns:
        JSON['service']: available or unavailable
    """
    service = get_url("clavardez")
    return JsonResponse({"service": service}, safe=False)


@login_required
def get_total_chats_per_month_for_this_year(request):
    """Return totel chats per month for this current year

    Args:
        request Request: HTTP Request header

    Returns:
        JSON: list of value per month [2345,4352, ...]
    """
    client = get_lh3_client_connection()
    if client == False:
        return HttpResponseRedirect(reverse("lh3_connection_error"))

    today = datetime.today()
    chats_report = client.chats()
    chats_for_this_year = chats_report.list_year(today.year)

    this_year_usage_per_month = list()
    for element in range(1, 13):
        holder_for_this_month = list()
        for item in chats_for_this_year:
            if parse(item.get("date")).month == element:
                if item.get("count") > 0:
                    holder_for_this_month.append(item.get("count"))
        if holder_for_this_month:
            this_year_usage_per_month.append(sum(holder_for_this_month))
    return JsonResponse(
        {"this_year_usage_per_month": this_year_usage_per_month}, safe=False
    )


@login_required
def get_total_chat_for_today(request):
    """return the total chat for today in JSON format

    Args:
        request Request: HTML header request

    Returns:
        String: total chats
    """
    client = get_lh3_client_connection()
    if client == False:
        return HttpResponseRedirect(reverse("lh3_connection_error"))

    today = datetime.today()
    total_chat_today = client.chats().list_day(
        year=today.year, month=today.month, day=today.day
    )

    return JsonResponse({"total_chats": len(total_chat_today)}, safe=False)


@login_required
def get_total_chat_for_this_month(request):
    """return the total chat for this current month in JSON format

    Args:
        request Request: HTML header request

    Returns:
        String: total chats
    """
    client = get_lh3_client_connection()
    if client == False:
        return HttpResponseRedirect(reverse("lh3_connection_error"))

    today = datetime.today()
    chats = client.chats().list_month(year=today.year, month=today.month)
    chats = [chat.get("day").get("count") for chat in chats]

    return JsonResponse({"total_chats": sum(chats)}, safe=False)


@login_required
def get_total_chat_for_this_year(request):
    """return the total chat for this current year in JSON format

    Args:
        request Request: HTML header request

    Returns:
        String: total chats
    """
    client = get_lh3_client_connection()
    if client == False:
        return HttpResponseRedirect(reverse("lh3_connection_error"))

    today = datetime.now()
    chats = client.chats().list_year(year=today.year)
    chats = [chat.get("count") for chat in chats]

    return JsonResponse({"total_chats": sum(chats)}, safe=False)


@login_required
def get_data_for_chart(request):
    """Return data for each month for the Chart on the Homepage (dashboard)

    Args:
        request Request: HTML header request

    Returns:
        JSON: return list for each mont (i.e last_year = [2344, 7009, 34244])
    """
    client = get_lh3_client_connection()
    if client == False:
        return HttpResponseRedirect(reverse("lh3_connection_error"))

    today = datetime.today()
    chats_last_year_per_month = chat_usage_per_month_for_a_past_year(
        client, today.year - 1
    )
    chats_two_years_ago_per_month = chat_usage_per_month_for_a_past_year(
        client, today.year - 2
    )
    chats_this_year_per_month = chat_usage_per_month_for_a_past_year(client, today.year)

    return JsonResponse(
        {
            "last_year": chats_last_year_per_month,
            "this_year": chats_this_year_per_month,
            "two_years_ago": chats_two_years_ago_per_month,
        },
        safe=False,
    )


@login_required
def get_operators_currently_online(request):
    """Return a list of operator username

    Args:
        request Request: HTML request header

    Returns:
        list: list of operator username
    """
    client = get_lh3_client_connection()
    if client == False:
        return HttpResponseRedirect(reverse("lh3_connection_error"))

    client.set_options(version="v1")
    users = client.all("users").get_list()
    # {'type': 'user', 'id': 33045, 'name': 'guinsly_sp',
    ##   'email': None, 'show': 'dnd', 'status': 'troubleshooting'}
    users = [user for user in users if user.get("show") != "unavailable"]

    for user in users:
        user["status"] == "-"

    chats = find_chats_for_this_current_hour()

    for user in users:
        picked_up_chats_by_this_operator = (
            find_total_chat_for_this_current_hour_that_this_operator_had_picked_up(
                chats, user.get("name")
            )
        )
        user["answered"] = "{0}/{1}".format(
            picked_up_chats_by_this_operator, len(chats)
        )

    return JsonResponse(users, safe=False)


@login_required
def last_chats(request, *args, **kwargs):
    """Getting the last 2 days of chats.

    Args:
        request Request: http request

    Returns:
        JSON: dict of HTML string representing Chat metadata
    """

    today = datetime.today()
    last2Days = today - timedelta(days=2)

    client = get_lh3_client_connection()
    if client == False:
        return HttpResponseRedirect(reverse("lh3_connection_error"))

    chats = client.chats()
    to_date = (
        str(today.year) + "-" + "{:02d}".format(today.month) + "-" + str(today.day)
    )
    chats = chats.list_day(
        year=last2Days.year, month=last2Days.month, day=last2Days.day, to=to_date
    )

    chats = soft_anonimyzation(chats)
    chats = [Chats(chat) for chat in chats]

    response = {"data": []}
    counter = 0
    for chat in chats:
        counter += 1
        response.get("data").append(
            {
                "id": counter,
                "Guest": "<a href="
                + chat.chat_standalone_url
                + ' target="_blank">'
                + chat.guest[0:7]
                + " </a>",
                "Started": chat.started,
                "From Queue": '<a href="/search/chats/from/this/queue/for/this/year/using/only/the/queue_name/'
                + chat.queue
                + ' ">'
                + chat.queue
                + " </a>",
                "Operator": operator_is_not_none(
                    "/search/chats/answered/by/this/users/", chat.operator
                ),
                "Ended": check_if_Ended_is_none(chat.ended),
                "Transcript": '<a href="/search/chat/transcript/'
                + str(chat.chat_id)
                + ' "> Transcript</a>',
                "Wait": get_chat_wait(chat),
                "Duration": get_chat_duration(chat),
                "Protocol": get_protocol_icon(chat),
            }
        )
    return JsonResponse(
        response,
        safe=False,
    )


def check_production_database(request, *args, **kwargs):
    """Getting the last 2 days of chats.

    Args:
        request Request: http request

    Returns:
        JSON: dict of HTML string representing Chat metadata
    """
    try:
        import mysql.connector

        db_result = chatReferenceQuestion.objects.using("cronjobDB")
        result = True
    except:
        result = False
    response = {"connection": result}
    return JsonResponse(
        response,
        safe=False,
    )
