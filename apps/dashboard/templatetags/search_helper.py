import datetime
import random
import secrets
import time
import os
from collections import Counter
from datetime import datetime, timedelta
from random import shuffle
import re

from django import template
from django.utils.safestring import mark_safe


register = template.Library()


@register.simple_tag
def version_date():
    pass
    # return time.strftime('%m/%d/%Y %H:%M:%S', time.gmtime(os.path.getmtime('../.git')))


# from .daily_report_range import create_report, get_chat_for_this_day
from sp_ask_school import (
    find_school_abbr_by_queue_or_profile_name,
    find_school_by_operator_suffix,
)
from dateutil.parser import parse


@register.simple_tag
def get_right_time(chat_datetime):
    if chat_datetime:
        chat_datetime = parse(chat_datetime)
        d = chat_datetime - timedelta(hours=4)

        return d.strftime("%Y-%m-%d %H:%M:%S")
    return chat_datetime


@register.filter(name="highlight_search")
def highlight_search(value, query):
    # Use regular expressions to find and replace the query with highlighted HTML
    highlighted = re.sub(
        r"(" + re.escape(query) + r")",
        r'<span class="highlight">\1</span>',
        value,
        flags=re.IGNORECASE,
    )
    return highlighted


@register.simple_tag
def get_this_shift_time():
    this_hour = int(datetime.today().strftime("%H"))
    next_hour = this_hour + 1
    this_shift = "for {0}-{1}".format(str(this_hour), str(next_hour))
    return this_shift


@register.simple_tag
def get_right_time_short_version(chat_datetime):
    if chat_datetime:
        chat_datetime = parse(chat_datetime)
        d = chat_datetime - timedelta(hours=4)

        return d.strftime("%Y-%m-%d")
    return chat_datetime


@register.simple_tag
def get_right_time_hours(chat_datetime):
    if chat_datetime:
        chat_datetime = parse(chat_datetime)
        d = chat_datetime - timedelta(hours=4)

        return d.strftime(" %H:%M:%S")
    return chat_datetime


@register.simple_tag
def get_new_tab_transcript_link(guest):
    return guest


@register.simple_tag
def get_duration_from_2_timestamps(started, ended):
    if not ended:
        return ""
    if not started:
        return ""
    started = started.strftime("%H:%M:%S")
    ended = ended.strftime("%H:%M:%S")
    total_time = datetime.datetime.strptime(
        ended, "%H:%M:%S"
    ) - datetime.datetime.strptime(started, "%H:%M:%S")
    return total_time


@register.simple_tag
def get_protocol(protocol):
    if "web":
        return '<i class="fas fa-comments"></i>'
    elif "twilio":
        return '<i class="fas fa-sms"></i>'
    else:
        return '<i class="fas fa-mobile-alt"></i>'


@register.simple_tag
def get_new_window_url_for_transcript(lh3id):
    return "https://ca.libraryh3lp.com/dashboard/queues/ANYTHING/calls/ANYTHING/" + str(
        lh3id
    )


@register.simple_tag
def random_operator_status():
    return secrets.choice(["busy", "available", "selecting queue"])


@register.simple_tag
def print_timestamp():
    # specify format here
    return time.now.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.now))


@register.simple_tag
def find_school_from_username(operator_username):
    return find_school_by_operator_suffix(operator_username)


@register.simple_tag
def find_school_from_queue_name(queue_name):
    return find_school_abbr_by_queue_or_profile_name(queue_name)


@register.simple_tag
def get_duration_from_2_timestamps(started, ended):
    if not ended:
        return ""
    if not started:
        return ""
    started = started.strftime("%H:%M:%S")
    ended = ended.strftime("%H:%M:%S")
    total_time = datetime.datetime.strptime(
        ended, "%H:%M:%S"
    ) - datetime.datetime.strptime(started, "%H:%M:%S")
    return total_time


"""	 
@register.simple_tag
def find_avatar_for_school(operator_username):
	school =  find_school_by_operator_suffix(operator_username)

@register.simple_tag
def verify_if_this_chat_has_a_reference_question(chat_id):
	chat =  Chat.objects.filter(id__exact=chat_id).first()
	transcript =  Transcript.objects.filter(chat__exact=chat).first()
	if transcript:
		return True
	else:
		return False
"""
