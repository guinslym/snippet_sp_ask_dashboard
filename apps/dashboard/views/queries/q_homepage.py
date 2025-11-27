import json
from datetime import datetime, timedelta, timezone

from sp_ask_school import (
    find_queues_from_a_school_name,
    find_school_by_operator_suffix,
    find_school_by_queue_or_profile_name,
)
from apps.dashboard.utils.utils import Chats, search_chats, soft_anonimyzation
from dateutil.parser import parse
from lh3.api import *


def query_for_homepage_recent_chats(client, today, number_of_days):
    given_date = today - timedelta(days=number_of_days)

    chats = client.chats()
    to_date = (
        str(today.year)
        + "-"
        + "{:02d}".format(today.month)
        + "-"
        + "{:02d}".format(today.day)
    )
    chats = chats.list_day(
        year=given_date.year, month=given_date.month, day=given_date.day, to=to_date
    )
    return chats
