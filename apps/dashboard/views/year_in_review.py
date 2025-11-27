import glob
import json
import os
import pathlib
import shutil
import zipfile
import calendar
import zlib
from datetime import datetime, timedelta, timezone, date
from os import path
from pathlib import Path
from pprint import pprint as print

from django.db.models import Q
from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.http.response import JsonResponse
from django.shortcuts import render
from django.contrib import messages

import lh3.api
import pandas as pd
from bs4 import BeautifulSoup
from apps.dashboard.models import chatReferenceQuestion
from sp_ask_school import (
    find_queues_from_a_school_name,
    find_school_by_operator_suffix,
    find_school_by_queue_or_profile_name,
    FRENCH_QUEUES,
    SMS_QUEUES,
)

from apps.dashboard.utils.daily_report import real_report

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


from dateutil.parser import parse
from lh3.api import *
from core.settings.base import BASE_DIR

import calplot
import pandas as pd
import pandas as pd
import numpy as np
import json
import pylab
from django.contrib.auth.decorators import login_required
from lh3.api import *
from datetime import datetime, timedelta
import dateutil.relativedelta

from django.contrib.auth.decorators import login_required


def remove_practice_queues(chats_this_day):
    res = [chat for chat in chats_this_day if not "practice" in chat.get("queue")]
    return res


def french_queues(chats):
    french = list()
    for chat in chats:
        if chat.get("queue") in FRENCH_QUEUES:
            french.append(chat)
    return french


def sms_queues(chats):
    sms = list()
    for chat in chats:
        if chat.get("queue") in SMS_QUEUES:
            sms.append(chat)
    return sms


def survey_column_to_analyzed(filtered_data_adjusted, column_title):
    # Calculate the percentages of "Yes" and "No" responses
    response_percentages = (
        filtered_data_adjusted[column_title].value_counts(normalize=True) * 100
    )

    # Convert the percentages to a dictionary
    percentage_dict = response_percentages.to_dict()

    return percentage_dict


@login_required
def year_in_review(request):
    # Load the CSV file containing the survey data
    file_path = "exit_survey.csv"  # Replace with your actual file path
    df = pd.read_csv(file_path)

    # Convert "Date submitted" to datetime format
    df["Date submitted"] = pd.to_datetime(df["Date submitted"], errors="coerce")

    # Define the date range for filtering
    start_date_adjusted = pd.Timestamp("2022-09-01")
    end_date_adjusted = pd.Timestamp("2023-08-31")

    # Filter the data for the specified date range
    filtered_data_adjusted = df[
        (df["Date submitted"] >= start_date_adjusted)
        & (df["Date submitted"] <= end_date_adjusted)
    ]

    # Further filter out NaN or blank responses from the "Was this your first time using the service?" column
    filtered_data_adjusted = filtered_data_adjusted.dropna(
        subset=["Was this your first time using the service?"]
    )

    result = dict()
    column_title = "Was this your first time using the service?"
    result["first_time"] = survey_column_to_analyzed(
        filtered_data_adjusted, column_title
    )

    column_title = "This chat service is..."
    result["chat_service_is"] = survey_column_to_analyzed(
        filtered_data_adjusted, column_title
    )

    column_title = "What is your academic status?"
    result["academic_status"] = survey_column_to_analyzed(
        filtered_data_adjusted, column_title
    )

    column_title = "The service provided by the librarian was..."
    result["provided_by_the_librarian"] = survey_column_to_analyzed(
        filtered_data_adjusted, column_title
    )

    column_title = "The librarian provided me with..."
    result["provided_me_with"] = survey_column_to_analyzed(
        filtered_data_adjusted, column_title
    )

    column_title = "Would you use this service again?"
    result["would_use_again"] = survey_column_to_analyzed(
        filtered_data_adjusted, column_title
    )

    column_title = "Where were you when you chatted with us today?"
    result["where_were_you"] = survey_column_to_analyzed(
        filtered_data_adjusted, column_title
    )

    client = get_lh3_client_connection()
    if client == False:
        return HttpResponseRedirect(reverse("lh3_connection_error"))

    client = Client()
    today = datetime.today()
    chats = client.chats()
    chats = chats.list_day(year=2022, month=9, day=1, to="2023-08-31")
    chats_this_day = remove_practice_queues(chats)
    unanswered_chats = [chat for chat in chats_this_day if chat.get("accepted") is None]

    answered_chats = [chat for chat in chats_this_day if chat.get("accepted") != None]

    result["french_chats"] = len(french_queues(answered_chats))
    result["sms_chats"] = len(sms_queues(answered_chats))

    result["answered_chats_nbr"] = len(answered_chats)

    df = pd.DataFrame(chats)

    # Removing unecessary column
    del df["reftracker_id"]
    del df["reftracker_url"]
    del df["desktracker_id"]
    del df["desktracker_url"]
    del df["referrer"]
    del df["ip"]

    # answered chats only
    df = df[df["operator"].notna()]

    # Only chats in protocol: web; twillio; sms
    df = df[df["protocol"].isin(["web", "sms", "twillio"])]

    # Removing practice queues
    df = df.drop(df[df["queue"] == "practice-webinars"].index)
    df = df.drop(df[df["queue"] == "practice-webinars-fr"].index)
    df = df.drop(df[df["queue"] == "practice-webinars-txt"].index)

    # Ensure the date column is in datetime format
    df["accepted"] = pd.to_datetime(df["accepted"])

    # Add month name
    df["month_name"] = df["accepted"].dt.strftime("%B")

    df_fr = df[df["queue"].isin(FRENCH_QUEUES)]
    df_sms = df[df["queue"].isin(SMS_QUEUES)]

    result["french_chats_df"] = df_fr.id.count()
    result["sms_chats_df"] = df_sms.id.count()
    result["english_chats_df"] = df.id.count() - df_fr.id.count()

    # df[0:6000].to_excel("year_in_review.xlsx", index=False)

    # Extract the month from the date column
    df["month"] = df["accepted"].dt.month

    # Aggregate the data by month
    result["monthly_breakdown"] = df.groupby("month_name").size()
    # print(result["monthly_breakdown"])

    for i in range(1, 31):
        date_of_interest = pd.Timestamp("2022-09-" + str(i))
        # print("Date: {0} /t{1}".format(str(i) , len(df[df['accepted'].dt.date == date_of_interest.date()])))

    date_of_interest = pd.Timestamp("2022-09-22")
    len(df[df["accepted"].dt.date == date_of_interest.date()])

    return render(
        request,
        "year_in_review.html",
        {
            "result": result,
        },
    )
