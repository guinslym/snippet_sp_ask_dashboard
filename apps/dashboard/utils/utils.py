import json
import re
import time

# time
from datetime import datetime, time, timedelta, timezone
from typing import List

from django.conf import settings
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect, render

import lh3.api
from bs4 import BeautifulSoup
from sp_ask_school import (
    find_school_by_operator_suffix,
    find_school_by_queue_or_profile_name,
)
from dateutil import parser, relativedelta, tz
from dateutil.parser import parse
from lh3.api import *

default_date = datetime.combine(
    datetime.now(), time(0, tzinfo=tz.gettz("America/New_York"))
)


def debug_log(print_output):
    """
    Print output if debug is on
    Can be single item or list
    """
    DEBUG = getattr(settings, "DEBUG", None)
    if DEBUG:
        if type(print_output) is list:
            for line in print_output:
                print(line)
        else:
            print(print_output)


content_range_pattern = re.compile(r"chats (\d+)-(\d+)\/(\d+)")


def render_this(request, my_html_template, my_results):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            my_results,
            safe=False,
        )
    return render(request, my_html_template, my_results)


def create_heatmap_data(chats):
    heatmap = [
        parse(chat.get("started")).replace(tzinfo=timezone.utc).timestamp()
        for chat in chats
    ]
    counter = {x: heatmap.count(x) for x in heatmap}
    heatmap_chats = json.dumps(counter)

    return heatmap_chats


def operator_is_not_none(url, operator_username):
    """return a TUPLE representing a HTML Links to search an Operator past answered chats

    Args:
        url (_type_): part of this web app url '/search/chats/answered/by/this/users/'
        operator_username (_type_): _description_

    Returns:
        String: full HTML link i.e. '<a href=/search/chats/answered/by/this/users/margot_york ">margot_york </a>'
    """
    if operator_username:
        return (
            "<a href=" + url + operator_username + ' ">' + operator_username + " </a>",
        )
    return None


def check_if_Ended_is_none(chat_ended_timevalue):
    """Return Tuple representing the End time of the chats (i.e. ('22:06:26',))

    Args:
        chat_ended_timevalue (_type_): _description_

    Returns:
        Tuple: end of time of the chats ('22:06:26',) or ''
    """
    if chat_ended_timevalue:
        return (chat_ended_timevalue.split(" ")[1],)
    return " "


def get_chat_wait(chat):
    """Return the chat waiting time in seconds before an operator has picked up the chat

    Args:
        chat Chat: object

    Returns:
        string: The chat wait time i.e. "11 secs" or ''
    """
    try:
        if chat.wait:
            return chat.wait
    except:
        return " "


def get_chat_duration(chat):
    """Return the chat duration

    Args:
        chat Chat:string format representing the time

    Returns:
        string: the chat duration i.e.  "9 min 33 secs"
    """
    try:
        if chat.duration:
            return chat.duration
    except:
        return " "


def get_protocol_icon(chat):
    """Return the HTML script for an ICON representing the chat prototol (i.e SMS icon)

    Args:
        chat Chat: object

    Returns:
        string: Font-awesome HTML script
    """
    if chat.protocol == "web":
        return ' <i class="fas fa-2x  fa-comments"></i>'
    elif chat.protocol == "sms":
        return '<i class="fas fa-2x fa-sms"></i>'
    elif chat.protocol == "twillio":
        return '<i class="fas fa-2x fa-sms"></i>'
    else:
        return '<i class="fas fa-2x  fa-comments"></i>'


def get_url(queue):
    """Return the JSON content of an HTML (LibraryH3lp API endpoint)

    Args:
        queue String: queue name

    Returns:
        string: return string i.e. "unavailable"
    """
    url = (
        "https://ca.libraryh3lp.com/presence/jid/"
        + queue
        + "/chat.ca.libraryh3lp.com/text"
    )
    response = requests.get(url).content
    return response.decode("utf-8")


def extract_content_range(content_range):
    if not content_range or content_range == "chats 0-0/0":
        return ("0", "0", "0")  # Default values for begin, end, total
    
    matches = content_range_pattern.match(content_range)
    if not matches:
        debug_log(f"Failed to parse Content-Range: {content_range}")
        return ("0", "0", "0")  # Fallback if regex fails
    
    begin = matches.group(1)
    end = matches.group(2)
    total = matches.group(3)
    return (begin, end, total)


def search_chats(client, query, chat_range):
    begin, end = chat_range
    _, x_api_version = lh3.api._API.versions.get("v4")
    headers = {
        "Content-Type": "application/json",
        "Range": f"chats {begin}-{end}",
        "X-Api-Version": x_api_version,
    }

    request = getattr(client.api().session, "post")
    response = request(
        client.api()._api("v4", "/chat/_search"), headers=headers, json=query
    )
    
    # Check if response is successful
    if response.status_code != 200:
        debug_log(f"API request failed with status {response.status_code}: {response.text}")
        return [], ("0", "0", "0")  # Return empty chats and default content range

    chats = client.api()._maybe_json(response)
    
    # Safely get Content-Range header with a fallback
    content_range = response.headers.get("Content-Range", "chats 0-0/0")
    try:
        content_range = extract_content_range(content_range)
    except AttributeError:
        debug_log("Invalid Content-Range header format, using default")
        content_range = ("0", "0", "0")  # Fallback if parsing fails

    return chats, content_range


class Chats(object):
    def __init__(self, chat):
        self.operator = chat.get("operator", "")
        self.guest = chat.get("guest")
        self.started = None
        self.ended = ""

        # check local_ first then check 'started'
        if "local_started" in chat.keys():
            self.started = parser.parse(
                chat.get("local_started"),
                default=datetime(2017, 10, 13, tzinfo=tz.gettz("America/New_York")),
            ).strftime("%Y-%m-%d %H:%M:%S")
        else:
            # consider that it's already local i.e. Homepage call
            self.started = parser.parse(
                chat.get("started"),
                default=datetime(2017, 10, 13, tzinfo=tz.gettz("America/New_York")),
            ).strftime("%Y-%m-%d %H:%M:%S")

        if "local_ended" in chat.keys():
            if chat.get("local_ended"):
                self.ended = parser.parse(
                    chat.get("local_ended"),
                    default=datetime(2017, 10, 13, tzinfo=tz.gettz("America/New_York")),
                ).strftime("%Y-%m-%d %H:%M:%S")
            else:
                self.ended = ""
        else:
            if chat.get("ended"):
                self.ended = parser.parse(
                    chat.get("ended"),
                    default=datetime(2017, 10, 13, tzinfo=tz.gettz("America/New_York")),
                ).strftime("%Y-%m-%d %H:%M:%S")
            else:
                self.ended = ""

        self.protocol = chat.get("protocol")
        self.school = None
        if chat.get("accepted"):
            self.school = find_school_by_operator_suffix(chat.get("operator"))
        self.duration = None
        if self.started and self.ended:
            try:
                self.duration = parse(chat.get("ended").replace("+00:Z", "Z")) - parse(
                    chat.get("started").replace("+00:Z", "Z")
                )
                self.duration = timedelta(0, self.duration.seconds)
            except:
                pass
        if self.started and chat.get("accepted"):
            self.wait = parse(chat.get("accepted")) - parse(chat.get("started"))
            self.wait = timedelta(0, self.wait.seconds)
        self.queue_id = chat.get("queue_id")
        self.queue = chat.get("queue")
        self.chat_id = chat.get("id")
        self.chat_standalone_url = (
            "https://ca.libraryh3lp.com/dashboard/queues/{0}/calls/REDACTED/{1}".format(
                self.queue_id, self.chat_id
            )
        )

    def __repr__(self):
        """Return string representation of this Class."""
        return "<Chat Object: {0}>\n started: {1}\n ended: {2}\n queue: {3}\nduration: {4}\noperator: {5}\n".format(
            self.guest[0:5],
            self.started,
            self.ended,
            self.queue[0:5],
            self.duration,
            self.operator,
        )

    def __str__(self):
        """Return string representation of this Class for String call."""
        return "<Chats object started: {0}>".format(str(self.started))


def retrieve_transcript(transcript_metadata, chat_id):
    # import pdb;pdb.set_trace()
    print(transcript_metadata)
    if "<title>Error 500 </title>" in transcript_metadata:
        import pdb

        pdb.set_trace()
        return {
            "chat_id": chat_id,
            "message": "No Transcript found",
            "counter": 0,
            "chat_standalone_url": "https://ca.libraryh3lp.com/dashboard/queues/{0}/calls/REDACTED/{1}".format(
                queue_id, chat_id
            ),
            "guest": guest,
        }
    try:
        queue_id = transcript_metadata["queue_id"]
    except:
        breakpoint()
    guest = transcript_metadata["guest"].get("jid")
    get_transcript = (
        transcript_metadata["transcript"] or "<div>No transcript found</div>"
    )
    soup = BeautifulSoup(get_transcript, "html.parser")
    divs = soup.find_all("div")
    transcript = list()
    counter = 1
    for div in divs[1::]:
        try:
            transcript.append(
                {
                    "chat_id": chat_id,
                    "message": str(div),
                    "counter": counter,
                    "chat_standalone_url": "https://ca.libraryh3lp.com/dashboard/queues/{0}/calls/REDACTED/{1}".format(
                        queue_id, chat_id
                    ),
                    "guest": guest,
                }
            )
            counter += 1
        except:
            pass
    return transcript


def soft_anonimyzation(list_of_chat: List[dict]) -> List[dict]:
    chats = list()
    for chat in list_of_chat:
        try:
            chat.pop("desktracker_url", None)
            chat.pop("reftracker_id", None)
            chat.pop("ip", None)
            chat.pop("reftracker_url", None)
            chat.pop("desktracker_id", None)
        except:
            print("error on soft_anonymization")
            pass
        chats.append(chat)
    return chats


def operatorview_helper(operator: str) -> List[dict]:
    client = Client()
    client.set_options(version="v1")
    users = client.all("users")
    operator = [user for user in users.get_list() if user.get("name") == operator]
    try:
        operator_id = operator[0].get("id")
    except:
        return False  # operator not found
    return users.one(operator_id).all("assignments").get_list()


def helper_for_operator_assignments():
    client = Client()
    client.set_options(version="v1")
    users = client.all("users")

    num_users = 0
    operator_report = list()
    for user in users.get_list():
        # Is that user staffing any queue?
        staffing = False
        assignments = users.one(user["id"]).all("assignments").get_list()[0:3]
        for assignment in assignments[0:5]:
            assignment["school"] = find_school_by_queue_or_profile_name(
                assignment.get("queue")
            )
            operator_report.append(assignment)

    assignments = [
        {
            "queue": assign.get("queue"),
            "operator": assign.get("user"),
            "school": assign.get("school"),
        }
        for assign in operator_report
    ]
    return assignments


def find_last_weekend_date():
    """Find last weekend date

    Returns:
        list: list of datetime
    """
    today = datetime.now()
    start = today - timedelta((today.weekday() + 1) % 7)
    sat = start + relativedelta.relativedelta(weekday=relativedelta.SA(-1))
    last_sun = sat + relativedelta.relativedelta(weekday=relativedelta.SU(1))
    fri = start + relativedelta.relativedelta(weekday=relativedelta.FR(-1))
    # mon = start + relativedelta.relativedelta(weekday=relativedelta.MO(-1))
    return [fri, sat, last_sun]


def find_chats_for_this_current_hour():
    today = datetime.today()
    client = Client()
    chats = client.chats()

    to_date = (
        str(today.year) + "-" + "{:02d}".format(today.month) + "-" + str(today.day)
    )
    chats = chats.list_day(year=today.year, month=today.month, day=today.day)

    list_of_chats = list()

    for chat in chats:
        if parse(chat.get("started")).hour == today.hour:
            list_of_chats.append(chat)

    return list_of_chats


def find_total_chat_for_this_current_hour_that_this_operator_had_picked_up(
    list_of_chats, username
):
    count = 0
    for chat in list_of_chats:
        if chat.get("operator") == username:
            count += 1
    return count


def get_this_shift_time():
    this_hour = int(datetime.now().time().strftime("%I"))
    if this_hour == 11:
        this_hour = datetime.now().time().strftime("%I %p")  # 11 AM
    next_hour_raw = (datetime.now() + timedelta(hours=1)).strftime("%I %p")
    next_hour = int((datetime.now() + timedelta(hours=1)).strftime("%I"))

    # for afternoon
    if next_hour == 12:
        this_hour = datetime.now().time().strftime("%I %p")
        this_shift = "{0}-{1}".format(str(this_hour), str(next_hour_raw))
        return this_shift  # 11 AM - 12 PM

    # for everything else
    this_shift = "{0}-{1}".format(str(this_hour), str(next_hour))
    this_shift = this_shift + " " + next_hour_raw.split(" ")[1]
    return this_shift  # 1-2 PM


def get_lh3_client_connection():
    try:
        client = Client()
        all_queues = client.all("queues").get_list()
    except:
        all_queues = dict()

    counter = 0
    while counter < 3:
        # is this a dictionnary - or a HTML error message
        if isinstance(all_queues[0], dict):
            # if this is a dict - does I have at least 5 chat queues
            if len(all_queues) > 5:
                return client
        counter += 1
    # Redirect Page
    return False
