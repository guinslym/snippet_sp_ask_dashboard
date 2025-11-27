import json
import os
import pathlib
import random
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pickletools import pystring
from pprint import pprint as print
from shutil import rmtree
from tempfile import gettempdir
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
import pandas as pd
from bs4 import BeautifulSoup
from apps.dashboard.models import chatReferenceQuestion
from sp_ask_school import (
    find_queues_from_a_school_name,
    find_school_by_operator_suffix,
    find_school_by_queue_or_profile_name,
)
from apps.dashboard.utils.utils import (
    Chats,
    create_heatmap_data,
    find_last_weekend_date,
    operatorview_helper,
    render_this,
    retrieve_transcript,
    search_chats,
    soft_anonimyzation,
)
from apps.dashboard.views.queries.q_search import (
    query_for_chats_for_this_school_using_an_username,
    query_for_chats_for_this_school_using_this_queue_name,
    query_get_chat_received_on_this_day,
    query_get_chats_for_this_user,
    query_get_chats_from_yesterday,
)
from dateutil.parser import parse
from lh3.api import *
from core.settings.base import BASE_DIR

warnings.filterwarnings("ignore")


@login_required
def get_chat_received_on_this_day(request, *args, **kwargs):
    this_day = queue_name = kwargs.get("this_day", None)
    if this_day:
        result = query_get_chat_received_on_this_day(this_day)

    return render_this(
        request, my_html_template="results/chats.html", my_results=result
    )


@login_required
def get_calendar_form_for_chat_received_on_this_day(request, *args, **kwargs):
    this_day = request.GET.get("this_day", None)

    if not this_day:
        return render(
            request,
            "results/calendar_form.html",
        )
    else:
        this_day = request.GET.get("this_day", None)
        result = query_get_chat_received_on_this_day(this_day)

        return render_this(
            request, my_html_template="results/chats.html", my_results=result
        )


@login_required
def get_chats_for_this_school_using_an_username(request, *args, **kwargs):
    """Return all chats from a school using an operator username

    Args:
        request (Request): HTML Request header

    Returns:
        list: list of chats
    """

    username = kwargs.get("username", None)
    result = query_for_chats_for_this_school_using_an_username(username)

    return render_this(
        request, my_html_template="results/chats.html", my_results=result
    )


@login_required
def get_chats_for_this_school_using_this_queue_name(request, *args, **kwargs):
    """Return all chats from a school using a queue name

    Args:
        request (Request): HTML Request header

    Returns:
        list: list of chats
    """

    queue_name = kwargs.get("queue_name", None)
    # breakpoint()
    result = query_for_chats_for_this_school_using_this_queue_name(queue_name)
    # breakpoint()
    return render_this(
        request, my_html_template="results/chats_from_queues.html", my_results=result
    )


@login_required
def get_chats_from_this_queue_for_this_year_using_only_the_queue_name(
    request, *args, **kwargs
):
    queue_name = kwargs.get("queue_name", None)
    school = find_school_by_queue_or_profile_name(queue_name)
    client = Client()

    today = datetime.today()

    print("queue_name: {0}".format(queue_name))
    query = {
        "query": {
            "queue": [queue_name],
            "from": str(today.year) + "-01-01",
            "to": str(today.year) + "-12-31",
        },
        "sort": [{"started": "descending"}],
    }
    queue_chats, content_range = search_chats(client, query, chat_range=(0, 500))
    # breakpoint()
    chats = soft_anonimyzation(queue_chats)
    today = datetime.today()
    current_year = today.year
    total_chats = len(chats)

    heatmap = [
        parse(chat.get("started")).replace(tzinfo=timezone.utc).timestamp()
        for chat in chats
    ]
    counter = {x: heatmap.count(x) for x in heatmap}
    heatmap_chats = json.dumps(counter)
    # print(chats)
    chats = [Chats(chat) for chat in chats]

    ref_questions = chatReferenceQuestion.objects.filter(
        Q(queue_name__exact=queue_name)
    ).values_list("lh3ChatID", flat=True)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "object_list": chats,
                "heatmap_chats": heatmap_chats,
                "username": queue_name,
                "get_chat_for_this_year": True,
                "current_year": current_year,
                "total_chats": total_chats,
                "ref_questions": ref_questions,
                "school": school,
                "show_download_reference_questions_button": True,
            },
            safe=False,
        )
    return render(
        request,
        "results/chats.html",
        {
            "object_list": chats,
            "get_chat_for_this_year": True,
            "heatmap_chats": heatmap_chats,
            "username": queue_name,
            "current_year": current_year,
            "total_chats": total_chats,
            "ref_questions": ref_questions,
            "school": school,
            "show_download_reference_questions_button": True,
        },
    )


@login_required
def get_chats_for_this_user(request, username):
    """find list of Chat answered by this user

    Args:
        request (Request): HTML Request Header
        username (string): operator username

    Returns:
        list: list of Chat objects by this user
    """
    client = Client()
    client.set_options(version="v1")

    today = datetime.today()
    chats = query_get_chats_for_this_user(client, username, today.year)

    # if the operator didn't answer any chat this year
    if not chats:
        # get chat for all year
        chats = query_get_chats_for_this_user(client, username, 2016)

    today = datetime.today()
    current_year = today.year
    total_chats = len(chats)

    assignments = operatorview_helper(username)
    if assignments == False:  # operator not found
        messages.warning(request, "The operator **{0}** doesn't exist".format(username))
        return HttpResponseRedirect("/")

        # return HttpResponseNotFound('<h1>This operator: "{0}" has not been found</h1>'.format(username))
    heatmap = [
        parse(chat.get("started")).replace(tzinfo=timezone.utc).timestamp()
        for chat in chats
    ]
    counter = {x: heatmap.count(x) for x in heatmap}
    heatmap_chats = json.dumps(counter)

    buddies = 0

    school = find_school_by_operator_suffix(username)
    users = client.all("users").get_list()
    operator_id = [user["id"] for user in users if user["name"] == username]
    ref_questions = chatReferenceQuestion.objects.filter(
        Q(operatorID__exact=operator_id[0])
    ).values_list("lh3ChatID", flat=True)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "chats": chats,
                "assignments": assignments,
                "get_chat_for_this_year": True,
                "heatmap_chats": heatmap_chats,
                "username": username,
                "current_year": current_year,
                "total_chats": total_chats,
                "buddies": buddies,
                "ref_questions": ref_questions,
                "school": school,
            },
            safe=False,
        )

    chats = [Chats(chat) for chat in chats]
    return render(
        request,
        "results/chats.html",
        {
            "object_list": chats,
            "assignments": assignments,
            "get_chat_for_this_year": True,
            "heatmap_chats": heatmap_chats,
            "username": username,
            "current_year": current_year,
            "total_chats": total_chats,
            "buddies": buddies,
            "ref_questions": ref_questions,
            "school": school,
        },
    )


@login_required
def get_chats_by_ip_address_using_this_chat_id(request, chat_id):
    client = Client()
    transcript_metadata = client.one("chats", chat_id).get()
    today = datetime.today()
    ip_address = transcript_metadata.get("ip")
    query = {
        "query": {
            "transcript": ["a"],
            "ip": [ip_address],
        },
        "sort": [{"started": "descending"}],
    }
    chats_from_users, content_range = search_chats(client, query, chat_range=(0, 500))
    chats = soft_anonimyzation(chats_from_users)

    return render(
        request,
        "results/chats.html",
        {
            "object_list": chats,
        },
    )


@login_required
def get_chats_for_this_user_for_this_year(request, username, information=None):
    client = Client()
    today = datetime.today()
    query = {
        "query": {
            "operator": [username],
            "from": str(today.year) + "-01-01",
            "to": str(today.year) + "-12-31",
        },
        "sort": [{"started": "descending"}],
    }
    chats_from_users, content_range = search_chats(client, query, chat_range=(0, 500))
    chats = soft_anonimyzation(chats_from_users)

    today = datetime.today()
    current_year = today.year
    total_chats = len(chats_from_users)

    assignments = operatorview_helper(username)
    heatmap = [
        parse(chat.get("started")).replace(tzinfo=timezone.utc).timestamp()
        for chat in chats
    ]
    counter = {x: heatmap.count(x) for x in heatmap}
    heatmap_chats = json.dumps(counter)

    school = find_school_by_operator_suffix(username)
    ref_questions = chatReferenceQuestion.objects.filter(
        Q(school__exact=school)
    ).values_list("lh3ChatID", flat=True)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "chats": chats,
                "assignments": assignments,
                "heatmap_chats": heatmap_chats,
                "username": username,
                "current_year": current_year,
                "total_chats": total_chats,
                "ref_questions": ref_questions,
            },
            safe=False,
        )
    chats = [Chats(chat) for chat in chats]
    return render(
        request,
        "results/chats.html",
        {
            "object_list": chats,
            "assignments": assignments,
            "heatmap_chats": heatmap_chats,
            "username": username,
            "current_year": 2022,
            "total_chats": total_chats,
            "ref_questions": ref_questions,
        },
    )


@login_required
def get_chats_for_this_queue(request, *args, **kwargs):
    """Return a JSON response of all chat from this queue

    Args:
        request Request: HTML request header

    Returns:
        JSON: List of dict of chats
    """
    client = Client()
    queue = kwargs.get("queue_name", None)
    today = datetime.today()
    until_this_day = str(today.year) + "-" + str(today.month) + "-" + str(today.day)
    query = {
        "query": {"queue": [queue], "from": "2016-01-01", "to": until_this_day},
        "sort": [{"started": "descending"}],
    }
    queue_chats = client.api().post("v4", "/chat/_search", json=query)
    chats = soft_anonimyzation(queue_chats)
    return JsonResponse(chats, safe=False)


@login_required
def get_chats_of_today(request, *args, **kwargs):
    client = Client()
    today = datetime.today()

    query = {
        "query": {"from": today.strftime("%Y-%m-%d")},
        "sort": [{"started": "ascending"}],
    }
    chats_from_users = client.api().post("v4", "/chat/_search", json=query)
    chats = soft_anonimyzation(chats_from_users)

    heatmap_chats = create_heatmap_data(chats)

    username = "Yesterday"
    # filter chats from yesteday only
    chats = [Chats(chat) for chat in chats]

    return render_this(
        request,
        "results/chats.html",
        {
            "object_list": chats,
            "heatmap_chats": heatmap_chats,
            "username": username,
            "current_year": "Yesterday",
            "total_chats": len(chats),
        },
    )


@login_required
def get_chats_from_yesterday(request, *args, **kwargs):
    client = Client()
    chats = client.chats()

    today = datetime.today()
    yesterday = today - timedelta(days=1)

    chats = chats.list_day(
        year=yesterday.year, month=yesterday.month, day=yesterday.day
    )
    chats = soft_anonimyzation(chats)

    heatmap_chats = create_heatmap_data(chats)

    username = "Yesterday"

    chats = [Chats(chat) for chat in chats]
    # return JsonResponse(chats, safe=False)

    return render_this(
        request,
        "results/chats.html",
        {
            "object_list": chats,
            "heatmap_chats": heatmap_chats,
            "username": username,
            "current_year": "Yesterday",
            "total_chats": len(chats),
        },
    )


@login_required
def get_chats_from_yesterday_from_mentees(request, *args, **kwargs):
    chats = query_get_chats_from_yesterday()

    chats = [chat for chat in chats if chat.get("accepted")]
    chats = [chat for chat in chats if "_int" in chat.get("operator")]

    heatmap_chats = create_heatmap_data(chats)

    username = "Mentees"

    chats = [Chats(chat) for chat in chats]

    return render_this(
        request,
        "results/chats.html",
        {
            "object_list": chats,
            "heatmap_chats": heatmap_chats,
            "username": username,
            "current_year": "Yesterday",
            "total_chats": len(chats),
        },
    )


@login_required
def get_chats_from_yesterday_sample_size(request, *args, **kwargs):
    chats = query_get_chats_from_yesterday()

    chats = random.sample(chats, int(len(chats) * 0.20))

    heatmap_chats = create_heatmap_data(chats)

    username = "Yesterday"

    chats = [Chats(chat) for chat in chats]

    return render_this(
        request,
        "results/chats.html",
        {
            "object_list": chats,
            "heatmap_chats": heatmap_chats,
            "username": username,
            "current_year": "Yesterday",
            "total_chats": len(chats),
        },
    )


@login_required
def download_get_chat_for_date_range(request, *args, **kwargs):
    filename = kwargs.get("filename", "")
    tmp_folder_name = kwargs.get("tmp_folder_name", "")
    # import pytest; pytest.set_trace()
    if filename:
        tmp = os.path.join(gettempdir(), ".{}".format(hash(int(tmp_folder_name))))
        filepath = str(pathlib.PurePath(tmp, filename))
        return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)
    else:
        raise Http404()


@login_required
def get_chat_for_date_range(request, *args, **kwargs):
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")
    if len(start_date) == 0:
        if len(end_date) == 0:
            return render(
                request, "results/search_between_date.html", {"object_list": None}
            )

    previous_date = None
    next_date = None
    if start_date and end_date:
        if start_date:
            start_date_with_time = parse(start_date)

        if end_date:
            end_date_with_time = parse(end_date)

        if end_date < start_date:
            messages.warning(
                request, "The End_date should be greater than the Start Date"
            )
            return render(
                request, "results/search_between_date.html", {"object_list": None}
            )

        previous_date = parse(start_date) - timedelta(days=1)
        next_date = parse(end_date) + timedelta(days=1)
        # API
        client = Client()
        chats = client.chats()
        to_date = (
            str(end_date_with_time.year)
            + "-"
            + "{:02d}".format(end_date_with_time.month)
            + "-"
            + str(end_date_with_time.day)
        )
        all_chats = chats.list_day(
            year=start_date_with_time.year,
            month=start_date_with_time.month,
            day=start_date_with_time.day,
            to=to_date,
        )

        # Tmp save the chats list
        df = pd.DataFrame(all_chats)
        del df["tags"]
        del df["referrer"]
        del df["id"]
        del df["profile"]
        del df["desktracker_id"]
        del df["reftracker_url"]
        del df["ip"]
        del df["reftracker_id"]
        del df["desktracker_url"]
        df["school_from_operator_username"] = df["operator"].apply(
            lambda x: find_school_by_operator_suffix(x)
        )
        df["school_from_queue_name"] = df["queue"].apply(
            lambda x: find_school_by_queue_or_profile_name(x)
        )
        df["guest"] = df["guest"].apply(lambda x: x.split("@")[0][0:8])

        today = datetime.today().strftime("%Y-%m-%d-%H:%M")

        tmp_folder_name = "4564565464321"
        rmtree(tmp_folder_name, ignore_errors=True)
        tmp = os.path.join(gettempdir(), ".{}".format(hash(4564565464321)))
        try:
            os.makedirs(tmp)
        except:
            pass

        filename = (
            "list_of_chats_from_date_range_results_"
            + str(random.randint(1, 7000))
            + ".xlsx"
        )
        filepath = str(pathlib.PurePath(tmp, filename))

        writer = pd.ExcelWriter(filepath, engine="xlsxwriter")
        df.to_excel(writer, index=False)
        writer.save()

        # Continue

        chats = [Chats(chat) for chat in all_chats]
        selected_chats = list()
        for chat in chats:
            if parse(chat.started) >= start_date_with_time:
                try:
                    if parse(chat.ended) <= end_date_with_time:
                        selected_chats.append(chat)
                except:
                    selected_chats.append(chat)
        return render(
            request,
            "results/search_between_date.html",
            {
                "object_list": selected_chats,
                "filename": filename,
                "tmp_folder_name": tmp_folder_name,
                "next_date": next_date,
                "previous_date": previous_date,
                "previous_date_string": str(previous_date),
                "next_date_string": str(next_date),
            },
        )
    else:
        messages.warning(request, "There should be a valid Start_Date and End_date")
    return render(request, "results/search_between_date.html", {"object_list": None})


@login_required
def search_chats_within_2_hours(request, *args, **kwargs):
    client = Client()
    chat_id = int(kwargs.get("chat_id", None))
    chat = client.one("chats", chat_id).get()

    if chat:
        start_date = parse(chat.get("started"))
        chats = client.chats()
        chats = chats.list_day(start_date.year, start_date.month, start_date.day)

        chat_within_2_hours = list()
        for chat in chats:
            started = parse(chat.get("started"))
            # print("{0} > {1} < {2}".format(started-timedelta(minutes=60), start_date , started+timedelta(minutes=60)))
            if started - timedelta(60) > start_date < started + timedelta(60):
                chat_within_2_hours.append(chats)

        # print(chat_within_2_hours)
        chats = None
        if chat_within_2_hours:
            chats = soft_anonimyzation(chat_within_2_hours)

        return JsonResponse(chats, safe=False)
    return JsonResponse(None, safe=False)


@csrf_exempt
@login_required
def search_chats_with_this_guestID(request, *args, **kwargs):
    guest_id = request.POST.get("guest_id", None)
    chats = None
    if guest_id:
        guest_id = guest_id.strip()
        if "@" in guest_id:
            pass
        else:
            guest_id = guest_id + "*"
        query = {
            "query": {
                "guest": [guest_id],
            },
            "sort": [{"started": "descending"}],
        }
        print(query)
        client = Client()
        chats = client.api().post("v4", "/chat/_search", json=query)
        chats = soft_anonimyzation(chats)
        chats = [Chats(chat) for chat in chats]
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"object_list": chats, "guest_id": guest_id})
        return render(
            request,
            "results/search_guest.html",
            {"object_list": chats, "guest_id": guest_id},
        )
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"object_list": None})
    return render(request, "results/search_guest.html", {"object_list": None})


class SearchGuestResultsView(TemplateView):
    template_name = "results/search_guest.html"


@login_required
def find_chat_with_this_guestID(request, *args, **kwargs):
    """return the list of Chat with that guestID

    Args:
        request Request: HTML request header

    Returns:
        list: return the list of Chat with that guestID
    """
    guest_id = kwargs.get("guest_id", None)
    chats = None
    if guest_id:
        if "@" in guest_id:
            pass
        else:
            guest_id = guest_id + "*"
        query = {
            "query": {
                "guest": [guest_id],
            },
            "sort": [{"started": "descending"}],
        }
        client = Client()
        chats = client.api().post("v4", "/chat/_search", json=query)
        # import pytest; pytest.set_trace()
        chats = soft_anonimyzation(chats)
        chats = [Chats(chat) for chat in chats]
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"object_list": chats, "guest_id": guest_id})
        return render(
            request,
            "results/search_guest.html",
            {"object_list": chats, "guest_id": guest_id},
        )
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"object_list": None})
    return render(request, "results/search_guest.html", {"object_list": None})


@login_required
def notify_blacklisted_ip_address(request, *args, **kwargs):
    guest_id = kwargs.get("guest_id", None)

    # TODO get list from a file
    blacklisted_ip_list = ["24.190", "24.44."]

    today = datetime.now()
    last30days = datetime.now() - timedelta(days=90)
    client = Client()
    chats = client.chats()
    to_date = (
        str(today.year) + "-" + "{:02d}".format(today.month) + "-" + str(today.day)
    )
    all_chats = chats.list_day(
        year=last30days.year,
        month=last30days.month,
        day=last30days.day,
        to=to_date,
    )

    selected_chats = []
    for chat in all_chats:
        try:
            if chat.get("ip", None)[0:6] in blacklisted_ip_list:
                selected_chats.append(chat)
        except:
            pass

    chats = soft_anonimyzation(selected_chats)
    chats = [Chats(chat) for chat in chats]

    return render(
        request,
        "results/search_between_date.html",
        {
            "object_list": chats,
            "next_date": None,
            "previous_date": None,
        },
    )


@login_required
def get_last_weekend_chats(request, *args, **kwargs):
    weekend = find_last_weekend_date()
    fri = weekend[0]
    sat = weekend[1]
    sun = weekend[2]

    client = Client()
    chats = client.chats()

    chats = chats.list_day(
        year=sat.year, month=sat.month, day=sat.day, to="{:%Y-%m-%d}".format(sun)
    )
    chats = soft_anonimyzation(chats)

    heatmap_chats = create_heatmap_data(chats)

    username = "Weekend"

    chats = [Chats(chat) for chat in chats]

    return render(
        request,
        "results/search_between_date.html",
        {
            "object_list": chats,
            "next_date": None,
            "previous_date": None,
        },
    )


@login_required
def find_duplicate_guest_id(request):
    client = Client()
    chats = client.chats()
    today = datetime.today()
    chats = chats.list_day(
        year=2016, month=1, day=1, to="{0}".format(today.strftime("%Y-%m-%d"))
    )
    df = pd.DataFrame(chats)
    guests = [chat["guest"] for chat in chats]
    result = pd.Series(guests).value_counts()
    data = pd.DataFrame({"guest": result.index, "occurence": result.values})
    data = data.loc[data["occurence"] > 5]

    data = data[0:5]

    result = pd.merge(data, df, on="guest", how="inner")
    result = result.to_dict()
    return result

    # count occurrences a particular column
    occur = data.groupby(["guest"]).size()

    # display occurrences of a particular column
    display(occur.sort_values(by="guest", ascending=False))

    df.groupby(["guest"]).agg({"guest": sum})

    return chats


# @login_required
def get_chats_by_exit_survey_timestamp(request, *args, **kwargs):
    timestamp = kwargs.get("timestamp", "08-01-2023 16:08:48")
    search_date = parse("08-01-2023 16:58:48")
    search_date_start = search_date - timedelta(seconds=1500)
    search_date_end = search_date + timedelta(seconds=1500)

    client = Client()
    chats = client.chats()

    chats = chats.list_day(
        year=search_date.year, month=search_date.month, day=search_date.day
    )

    result = sorted(
        (k, v)
        for k, v in chats.iteritems()
        if search_date_start <= k <= search_date_end
    )
    import pdb

    pdb.set_trace()
    df = pd.DataFrame(chats)

    start_date = pd.to_datetime(str(search_date_start))
    end_date = pd.to_datetime(str(search_date_end))
    df = df.loc[(df["started"] > str(start_date)) & (df["started"] < str(end_date))]

    result = sorted(
        (k, v)
        for k, v in chats.iteritems()
        if search_date_start <= k <= search_date_end
    )
    return HttpResponse("Hello {0}".format(len(df)))
