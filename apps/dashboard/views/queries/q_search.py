import json
from datetime import datetime, timedelta, timezone
import pandas as pd

import seaborn as sns
import matplotlib.pyplot as plt


from django.db.models import Q

from apps.dashboard.models import chatReferenceQuestion
from sp_ask_school import (
    find_queues_from_a_school_name,
    find_school_by_operator_suffix,
    find_school_by_queue_or_profile_name,
    sp_ask_school_dict,
)
from apps.dashboard.utils.utils import Chats, search_chats, soft_anonimyzation
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from lh3.api import *

from apps.dashboard.utils.utils import Chats, search_chats, soft_anonimyzation


def query_for_chats_for_this_school_using_an_username(username):
    client = Client()
    school_name = find_school_by_operator_suffix(username).lower()
    queues_from_school = find_queues_from_a_school_name(school_name)

    query = {
        "query": {
            "queue": queues_from_school,
            "from": "2021-01-01",
            "to": "2024-12-31",
        },
        "sort": [{"started": "descending"}],
    }
    queue_chats = client.api().post("v4", "/chat/_search", json=query)
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

    ref_questions = list(
        chatReferenceQuestion.objects.get(school=school_name).values_list(
            "lh3ChatID", flat=True
        )
    )

    return {
        "object_list": chats,
        "heatmap_chats": heatmap_chats,
        "username": school_name,
        "current_year": current_year,
        "total_chats": total_chats,
        "ref_questions": ref_questions,
        "school": school_name,
    }


def query_for_chats_for_this_school_using_this_queue_name(queue_name):
    client = Client()
    school_name = find_school_by_queue_or_profile_name(queue_name)
    queues_from_school = find_queues_from_a_school_name(school_name)

    ref_questions = list(
        chatReferenceQuestion.objects.filter(
            queue_name__in=queues_from_school
        ).values_list("lh3ChatID", flat=True)
    )
    # breakpoint()
    from_last_12_month = (datetime.today() + relativedelta(months=+12)).strftime(
        "%Y-%m-%d"
    )
    to_today = datetime.today().strftime("%Y-%m-%d")
    query = {
        "query": {
            "queue": queues_from_school,
            # "from": "2016-09-01",
            "from": str(datetime.today().year) + "-01-01",
            "to": to_today,
        },
        "sort": [{"started": "descending"}],
    }

    qty = 5000
    if "oronto" in school_name:
        qty = 3000
    queue_chats, content_range = search_chats(client, query, chat_range=(0, qty))

    chats = soft_anonimyzation(queue_chats)
    today = datetime.today()
    current_year = today.year

    heatmap = [
        parse(chat.get("started")).replace(tzinfo=timezone.utc).timestamp()
        for chat in chats
    ]
    counter = {x: heatmap.count(x) for x in heatmap}
    heatmap_chats = json.dumps(counter)
    chats = [Chats(chat) for chat in chats]

    # reverify that it's from the same year
    # chats = [chat for chat in chats if parse(chat.started).year == today.year]

    total_chats = len(chats)

    return {
        "object_list": chats,
        "heatmap_chats": heatmap_chats,
        "username": school_name,
        "current_year": current_year,
        "total_chats": total_chats,
        "ref_questions": ref_questions,
        "school": school_name,
    }


def query_get_chat_received_on_this_day(this_day):
    client = Client()

    query = {
        "query": {
            "from": this_day,
            "to": this_day,
        },
        "sort": [{"started": "descending"}],
    }
    # queue_chats = client.api().post("v4", "/chat/_search", json=query)

    queue_chats, content_range = search_chats(client, query, chat_range=(0, 500))

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

    return {
        "object_list": chats,
        "heatmap_chats": heatmap_chats,
        "username": this_day,
        "current_year": current_year,
        "total_chats": total_chats,
        "school": this_day,
    }


def query_get_chats_for_this_user(client, username, this_year):
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
    return chats


def query_get_chats_from_yesterday():
    client = Client()
    chats = client.chats()

    today = datetime.today()
    yesterday = today - timedelta(days=1)

    chats = chats.list_day(
        year=yesterday.year, month=yesterday.month, day=yesterday.day
    )
    chats = soft_anonimyzation(chats)

    return chats
