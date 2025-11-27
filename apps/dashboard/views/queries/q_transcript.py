import ipaddress

from django.db.models import Q

from bs4 import BeautifulSoup
from apps.dashboard.models import chatReferenceQuestion
from sp_ask_school import (
    find_queues_from_a_school_name,
    find_school_by_operator_suffix,
    find_school_by_queue_or_profile_name,
    sp_ask_school_dict,
)
from apps.dashboard.utils.utils import (
    Chats,
    retrieve_transcript,
    search_chats,
    soft_anonimyzation,
)
from dateutil.parser import parse
from lh3.api import *
from datetime import datetime, time, timedelta, timezone
from pprint import pprint as print
import pytz

utc = pytz.UTC


def query_for_transcript_that_was_transferred(results=(0, 100)):
    query = {
        "query": {
            "transcript": ["System message: transferring"],
        },
        "sort": [{"started": "descending"}],
    }
    client = Client()
    chats, content_range = search_chats(client, query, chat_range=results)
    chats = soft_anonimyzation(chats)
    chats = [Chats(chat) for chat in chats]
    return chats


def query_for_transcript_that_contains_file_transfer(results=(0, 100)):
    query = {
        "query": {
            "transcript": ["System message: download from"],
        },
        "sort": [{"started": "descending"}],
    }
    client = Client()
    chats, content_range = search_chats(client, query, chat_range=results)
    chats = soft_anonimyzation(chats)
    chats = [Chats(chat) for chat in chats]
    return chats


def query_for_search_transcript_with_this_keyword(in_transcript, results=(0, 500)):
    query = {
        "query": {
            "transcript": [in_transcript],
        },
        "sort": [{"started": "descending"}],
    }
    # import pdb; pdb.set_trace()
    client = Client()
    chats, content_range = search_chats(client, query, chat_range=results)
    # return chats
    chats = soft_anonimyzation(chats)
    chats = [Chats(chat) for chat in chats]
    return chats


def query_for_search_transcript_with_this_ip_address(ip_address, results=(0, 500)):
    # Not sure if this is a breach to privacy if I am searching by IP address.

    # you can search by IP as long as you also do a transcript search.
    #  I recommend setting that to commonly used a word like "the of an or a"
    query = {
        "query": {
            "transcript": ["a"],
            "ip": [ip_address],
        },
        "sort": [{"started": "descending"}],
    }

    client = Client()

    chats, content_range = search_chats(client, query, chat_range=results)
    # return chats
    chats = soft_anonimyzation(chats)
    chats = [Chats(chat) for chat in chats]
    return chats


def validate_ip_address(ip_string):
    try:
        ip_object = ipaddress.ip_address(ip_string)
        return True
    except ValueError:
        return False


def query_for_search_transcript_with_in_multifield_form(request, results=(0, 500)):
    # Not sure if this is a breach to privacy if I am searching by IP address.

    ip_address = request.POST.get("ip_address", None)
    guest_id = request.POST.get("guest_id", None)
    in_transcript = request.POST.get("in_transcript", None)
    start_date = request.POST.get("start_date", None)
    end_date = request.POST.get("end_date", None)
    operator = request.POST.get("operator", None)
    school = request.POST.get("school", None)

    # you can search by IP as long as you also do a transcript search.
    #  I recommend setting that to commonly used a word like "the of an or a"

    list_of_request_variable_to_check = [
        in_transcript,
        ip_address,
        start_date,
        end_date,
    ]

    query = {"sort": [{"started": "descending"}]}

    has_start_date = False
    has_end_date = False
    has_school = False
    has_operator = False

    if ip_address:
        if validate_ip_address(ip_address):
            query["ip"] = [ip_address]
        else:
            print("wrong ip address")
    if in_transcript:
        query["transcript"] = [in_transcript]
    else:
        # if I am looking for IP Address only, I need to add something in transcript.
        query["transcript"] = ["a"]
    if guest_id:
        guest_id = guest_id.strip()
        if "@" in guest_id:
            pass
        else:
            guest_id = guest_id + "*"
        query["guest"] = [guest_id]
    if start_date:
        query["from"] = start_date.split(" ")[0]
        has_start_date = True
    if end_date:
        query["to"] = end_date.split(" ")[0]
        has_end_date = True

    if school:
        query["queue"] = find_queues_from_a_school_name(school)

    if operator:
        has_operator = True
        query["operator"] = [operator.strip()]

    query = {"query": query}
    client = Client()

    chats, content_range = search_chats(client, query, chat_range=results)
    # return chats
    # breakpoint()
    chats = soft_anonimyzation(chats)
    list_of_chats = list()
    try:
        for chat in chats:
            list_of_chats.append(Chats(chat))
    except:
        print(chat.get("guest"))

    return list_of_chats


def query_for_get_transcript(chat_id=None):
    client = Client()
    transcript_metadata = client.one("chats", chat_id).get()
    transcript = retrieve_transcript(transcript_metadata, chat_id)
    queue_name = transcript_metadata.get("queue").get("name")
    started_date = parse(transcript_metadata.get("started")).strftime("%Y-%m-%d")

    # Chat Info
    try:
        operator = transcript_metadata.get("operator").get("name")
    except:
        operator = None
    try:
        referrer = transcript_metadata.get("referrer")
    except:
        referrer = None
    try:
        profile_avatar = transcript_metadata.get("profile").get("avatar")
    except:
        profile_avatar = None
    try:
        rollover_timeout = transcript_metadata.get("profile").get("rollover_timeout")
    except:
        rollover_timeout = None
    try:
        accepted = parse(transcript_metadata.get("accepted")).strftime("%H:%M:%S")
    except:
        accepted = None
    try:
        ended = parse(transcript_metadata.get("ended")).strftime("%H:%M:%S")
    except:
        ended = None
    try:
        started = parse(transcript_metadata.get("started")).strftime("%H:%M:%S")
    except:
        started = None
    guest_id = transcript_metadata.get("guest_id")
    guest = transcript_metadata.get("guest").get("jid")
    profile_id = transcript_metadata.get("profile_id")

    duration = None
    if started and ended:
        duration = parse(transcript_metadata.get("ended")) - parse(
            transcript_metadata.get("started")
        )
        duration = timedelta(0, duration.seconds)
    else:
        duration = None

    query = {
        "query": {
            "transcript": ["a"],
            "guest": [guest],
        },
        "sort": [{"started": "descending"}],
    }
    client = Client()
    chats, content_range = search_chats(client, query, chat_range=(0, 100))

    number_of_chat_occurence_by_guest_id = len(chats)

    if transcript_metadata.get("ip"):
        number_of_chat_occurence_by_guest_ip_address = len(
            query_for_search_transcript_with_this_ip_address(
                transcript_metadata.get("ip")
            )
        )
    else:
        number_of_chat_occurence_by_guest_ip_address = None

    simulteanous_chat = list()
    overlapping_chats = list()
    # pausing this computaton by getting out of the loop
    if operator and ended:
        # get the operator
        # get chat by this operator on that transcript day
        query = {
            "query": {
                "operator": [operator],
                "from": started_date,
                "to": started_date,
            },
            "sort": [{"started": "descending"}],
        }

        client = Client()
        chats, content_range = search_chats(client, query, chat_range=(0, 25))

        # import pdb; pdb.set_trace()
        for chat in chats:
            try:
                # Check if the chat overlaps with the specified time range
                result1 = parse(chat.get("started")) <= parse(
                    transcript_metadata.get("ended")
                )
                result2 = parse(chat.get("ended")) >= parse(
                    transcript_metadata.get("started")
                )
                result3 = parse(chat.get("ended")) >= parse(
                    transcript_metadata.get("started")
                )
                result4 = parse(chat.get("started")) <= parse(
                    transcript_metadata.get("ended")
                )

                if result1 and result2 or result3 and result4:
                    overlapping_chats.append(chat)
            except:
                # the chat has not yet ended.
                # don't calculate overlapping_chats
                pass

    if overlapping_chats:
        overlapping_chats = [Chats(chat) for chat in overlapping_chats]
        simulteanous_chat = overlapping_chats
    else:
        simulteanous_chat = None

    chat_transfered = None
    file_system_transfered = None
    constant_contact = None

    chat_message_positions = chatReferenceQuestion.objects.filter(
        Q(lh3ChatID__exact=chat_id)
    ).values_list("ref_question_position", flat=True)

    return {
        "object_list": transcript,
        "chat_message_positions": chat_message_positions,
        "queue_name": queue_name,
        "started_date": started_date,
        "chat_id": chat_id,
        "operator": operator,
        "referrer": referrer,
        "profile_avatar": profile_avatar,
        "rollover_timeout": rollover_timeout,
        "accepted": accepted,
        "ended": ended,
        "started": started,
        "guest_id": guest_id,
        "guest": guest,
        "profile_id": profile_id,
        "duration": duration,
        "simulteanous_chat": simulteanous_chat,
        "number_of_chat_occurence_by_guest_id": number_of_chat_occurence_by_guest_id,
        "number_of_chat_occurence_by_guest_ip_address": number_of_chat_occurence_by_guest_ip_address,
        "chat_transfered": chat_transfered,
        "file_system_transfered": file_system_transfered,
        "constant_contact": constant_contact,
    }


def query_for_download_transcript_in_html(chat_id=None):
    client = Client()
    transcript_metadata = client.one("chats", chat_id).get()
    transcript = retrieve_transcript(transcript_metadata, chat_id)

    url = "https://ca.libraryh3lp.com/dashboard/queues/"
    queue_id = str(transcript_metadata.get("queue").get("accunt_id")) + "/calls/"
    guest_id = (
        str(transcript_metadata.get("guest").get("jid"))
        + "/"
        + str(transcript_metadata.get("guest_id"))
    )
    url + queue_id + guest_id

    content = ["<html><body><h3 align='center'>Transcript</h3><hr/><br/><br>"]
    for msg in transcript:
        this_msg = msg.get("message")
        content.append(this_msg)

    return content


def query_for_add_this_as_a_reference_question(chat_id, position):
    client = Client()
    transcript_metadata = client.one("chats", chat_id).get()
    transcript = retrieve_transcript(transcript_metadata, chat_id)
    queue_name = transcript_metadata.get("queue").get("name")
    started_date = parse(transcript_metadata.get("started")).strftime("%Y-%m-%d")

    operator_username_id = transcript_metadata.get("operator", None)
    if operator_username_id:
        operator_username_id.get("account_id")
    queue_account_id = transcript_metadata.get("queue").get("account_id")

    result = chatReferenceQuestion.objects.filter(
        Q(lh3ChatID__exact=chat_id) & Q(ref_question_position__exact=int(position))
    ).first()

    if result:
        print("Found chat ID {0}".format(chat_id))
        # Reference Question already in DB
        # Delete object to remove the Reference Questions
        result.delete()
        # Return 0
        return 0
    else:
        print("NOT Found chat ID {0}".format(chat_id))
        # Reference Question NOT in DB
        # Create The CHAT and Return 1
        try:
            # TODO send that task to CELERY (Background job)
            chatReferenceQuestion.objects.create(
                lh3ChatID=chat_id,
                ref_question_found=True,
                ref_question_position=int(position),
                queue_name=transcript_metadata.get("queue").get("name"),
                queueID=transcript_metadata.get("queue").get("id"),
                operatorID=transcript_metadata.get("operator_id"),
            )
            return 1
        except:
            return 0
