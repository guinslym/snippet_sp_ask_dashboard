import glob
import json
import os
import pathlib
import shutil
import zipfile
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
from dashboard.models import chatReferenceQuestion
from dashboard.utils.ask_schools import (find_queues_from_a_school_name,
                                         find_school_by_operator_suffix,
                                         find_school_by_queue_or_profile_name)
from dashboard.utils.daily_report import real_report
from dashboard.utils.utils import (Chats, helper_for_operator_assignments,
                                   operatorview_helper, render_this,
                                   retrieve_transcript, search_chats,
                                   soft_anonimyzation)
from dateutil.parser import parse
from lh3.api import *
from settings.settings import BASE_DIR

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

import pandas as pd
from datetime import datetime

# Assuming 'lh3.api' is some client library you're using

@login_required
def get_report_page(request):
    # Assuming 'my_results' is some data you want to pass to the template
    my_results = dict()  # Replace with actual data you want to pass
    return render_this(request, my_html_template="results/all_report.html", my_results=my_results)

@login_required

def report_on_chats(request):
    client = Client()
    today = datetime.today()

    # Assuming you're fetching chats from the client
    chats = client.chats()

    # Get all chats starting from today up to 2016-01-01
    all_chats = chats.list_day(
        year=today.year, month=today.month, day=today.day, to="2016-01-01"
    )

    # Create a DataFrame from the list of chats
    df = pd.DataFrame(all_chats)

    # Select the relevant columns
    df = df[["id", "profile", "queue", "started", "ended", "accepted", "wait", "duration", "operator"]]

    df  = df[0:50]
    # Convert the DataFrame to a dictionary with 'records' orientation


    # Convert 'started' to datetime format and handle missing values
    df['started'] = pd.to_datetime(df['started'], errors='coerce')  # Coerce invalid dates to NaT (Not a Time)

    # Fill any missing values in 'started' with a default date, or you can leave them as NaT
    df['started'].fillna(pd.Timestamp('1970-01-01 00:00:00'), inplace=True)

    # Add 'year' and 'month_name' columns
    df['year'] = df['started'].dt.year
    df['month_name'] = df['started'].dt.strftime('%B')

    # Convert datetime columns to string format for JSON serialization
    df['started'] = df['started'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df['ended'] = pd.to_datetime(df['ended'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')


    df['school'] = df["queue"].apply(lambda x: find_school_by_queue_or_profile_name(x))
    

    chats_data = df.to_dict(orient='records')

    # Debugging: Print out the chats_data to make sure it's not empty or malformed
    print(chats_data)

    # Pass the chats data as JSON to the template
    return render(request, 'results/report_chats.html', {
        'user_queue_data': json.dumps(chats_data)  # Pass data as JSON
    })

def regenerate_and_save_chats_data(client, file_path):
    today = datetime.today()

    # Fetch chats from client API
    chats = client.chats()

    # Get all chats starting from today up to 2016-01-01
    all_chats = chats.list_day(
        year=today.year, month=today.month, day=today.day, to="2016-01-01"
    )

    # Create a DataFrame from the list of chats
    df = pd.DataFrame(all_chats)

    # Select the relevant columns
    df = df[["id", "profile", "queue", "started", "ended", "accepted", "wait", "duration", "operator"]]


    # Convert 'started' to datetime format
    df['started'] = pd.to_datetime(df['started'])

    # Add 'year' column
    df['year'] = df['started'].dt.year

    # Add 'month_name' column
    df['month_name'] = df['started'].dt.strftime('%B')

    df['school'] = df["queue"].apply(lambda x: find_school_by_queue_or_profile_name(x))

    # Convert the DataFrame to a dictionary with 'records' orientation
    chats_data = df.to_dict(orient='records')

    # Save the data to the JSON file
    with open(file_path, 'w') as json_file:
        json.dump(chats_data, json_file)
    print("Data regenerated and saved to file.")

    return chats_data


@login_required
def download_in_xslx_report__for_queues_assignment(request):
    client = lh3.api.Client()
    client.set_options(version='v1')

    # Get the list of users and queues
    users = client.all('users')
    queues_in_dict = client.all('queues').get_list()
    queues = [q.get('name').strip().lower() for q in queues_in_dict]  # Normalize queue names

    # Initialize the dictionary to store operator assignments with blank cells initially
    user_queue_dict = {user.get('name'): {queue: '' for queue in queues} for user in users.get_list()}

    # Iterate through each user and their assignments
    for user in users.get_list():
        user_name = user.get('name')
        assignments = users.one(user['id']).all('assignments').get_list()

        if assignments:
            for assignment in assignments:
                queue_name = assignment.get('queue')  # Get queue name
                if queue_name:  # Check if queue_name is not None
                    queue_name = queue_name.strip().lower()  # Normalize assignment queue name
                    if queue_name in user_queue_dict[user_name]:
                        user_queue_dict[user_name][queue_name] = 'TRUE'
                    else:
                        print(f"Queue '{queue_name}' not found for user '{user_name}'")  # Debug message
                else:
                    print(f"No queue_name found for assignment of user '{user_name}'")  # Handle missing queue_name



    # Save the DataFrame to an Excel file
    #

    print("Excel file has been created.")

    today = datetime.today().strftime("%Y-%m-%d")
    filename = "report-operator_queue_assignments-" + today + ".xlsx"
    filepath = str(pathlib.PurePath(BASE_DIR, "tmp_file", filename))

    # Convert the dictionary to a pandas DataFrame
    df = pd.DataFrame.from_dict(user_queue_dict, orient='index')


    # Create file using the UTILS functions
    df.to_excel(filepath, index_label="Operator",sheet_name="queue_assignement")

    # TODO: Create this report using a cronjob
    return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)


def regenerate_and_save_data(client, file_path):
    # Get the list of users and queues
    users = client.all('users')
    queues_in_dict = client.all('queues').get_list()
    queues = [q.get('name').strip().lower() for q in queues_in_dict]  # Normalize queue names

    # Initialize the list to store operator assignments
    user_queue_data = []

    # Iterate through each user and their assignments
    for user in users.get_list():
        user_name = user.get('name')
        assignments = users.one(user['id']).all('assignments').get_list()

        if assignments:
            for assignment in assignments:
                queue_name = assignment.get('queue')  # Get queue name
                if queue_name:  # Check if queue_name is not None
                    queue_name = queue_name.strip().lower()  # Normalize assignment queue name
                    user_queue_data.append({
                        'operator': user_name,
                        'queue': queue_name,
                        'assigned': True,
                        'school': find_school_by_operator_suffix(user_name)
                    })
        else:
            user_queue_data.append({
                        'operator': user_name,
                        'queue': None,
                        'assigned': False,
                        'school': find_school_by_operator_suffix(user_name)
                    })

    # Save the data to the JSON file
    with open(file_path, 'w') as json_file:
        json.dump(user_queue_data, json_file)
    print("Data regenerated and saved to file.")
    
    return user_queue_data

@login_required
def display_queue_assignments(request):
    client = Client()
    client.set_options(version='v1')

    # Define file path for cached data
    file_path = 'cached_user_queue_data.json'

    # Check if the JSON file exists and is from today
    if os.path.exists(file_path):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        if file_mod_time.date() == datetime.today().date():
            # If the file is from today, load the data from the file
            with open(file_path, 'r') as json_file:
                user_queue_data = json.load(json_file)
            print("Data loaded from cache.")
        else:
            user_queue_data = regenerate_and_save_data(client, file_path)
    else:
        user_queue_data = regenerate_and_save_data(client, file_path)

    # Pass the data to the template
    return render(request, 'results/queue_staffing.html', {
        'user_queue_data': json.dumps(user_queue_data)  # Pass data as JSON
    })




@login_required
def download_in_xslx_report__for_queues_for_this_year(request):
    # https://gitlab.com/libraryh3lp/libraryh3lp-sdk-python/-/blob/master/examples/scheduled-reports.py
    today = datetime.today()

    client = lh3.api.Client()
    chats_per_operator = client.reports().chats_per_queue(
        start="2021-01-01", end="2021-12-31"
    )

    print(chats_per_operator)

@login_required
def download_in_xslx_report_for_this_year(request):
    # https://gitlab.com/libraryh3lp/libraryh3lp-sdk-python/-/blob/master/examples/scheduled-reports.py
    today = datetime.today()

    client = lh3.api.Client()
    this_year = str(today.year)
    chats_per_operator = client.reports().chats_per_operator(
       start=this_year+"-01-01", end=this_year+"-12-31"
    )

    chats_per_operator = chats_per_operator.split("\r\n")
    chats_per_operator = chats_per_operator[1::]
    report = list()
    for data in chats_per_operator:
        if len(data) > 0:
            data = data.split(",")
            report.append(
                {
                    "operator": data[0],
                    "Total chat answered": data[1],
                    "Mean - of wait time (sec.)": data[2],
                    "Median - of wait time (sec.)": data[3],
                    "Min - of wait time (sec.)": data[4],
                    "Max - of wait time (sec.)": data[5],
                }
            )

    today = datetime.today().strftime("%Y-%m-%d")
    filename = "report-" + today + ".xlsx"
    filepath = str(pathlib.PurePath(BASE_DIR, "tmp_file", filename))

    df = pd.DataFrame(report)
    # Create file using the UTILS functions
    df.to_excel(filepath, index=False, sheet_name=this_year+"_report_for_operator")

    # TODO: Create this report using a cronjob
    return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)


@login_required
def chord_diagram(request):
    """
    client = Client()
    today = datetime.today()
    chats = client.chats()
    chats = chats.list_day(year=2021, month=1, day=1, to="2021-04-11")
    df = pd.DataFrame(chats)
    """

    return render(request, "chord_diagram.html")

@login_required
def daily_report(request):
    today = datetime.today().strftime("%Y-%m-%d")

    filename = "daily-" + today + ".xlsx"
    filepath = str(pathlib.PurePath(BASE_DIR, "tmp_file", filename))

    df = real_report()
    # Create file using the UTILS functions
    df.to_excel(filepath, index=False)

    # TODO: Create this report using a cronjob
    return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)

@login_required
def pivotTableOperatorAssignment(request):
    print("pivotTableOperatorAssignment")
    assignments = helper_for_operator_assignments()

    context = {"schools": assignments}

    df_assignements = pd.DataFrame(assignments)
    df_assignements["operator_copy_for_filtering"] = df_assignements["operator"]
    
    #how can I get last chat from the operator so that I can filter by Year in Excel. 
    usernames = [user.get('operator') for user in assignments]

    client = Client()
    today = datetime.today()

    new_data_list = list()
    
    #find the last chat for each operator
    for username in usernames:
        #get operator last chat

        query = {
            "query": {
                "operator": [username],
                "from": str(today.year-2) + "-01-01",
                "to": str(today.year) + "-12-31",
            },
            "sort": [{"started": "descending"}],
        }
        chats_from_users, content_range = search_chats(client, query, chat_range=(0, 500))
        
        #get the year of the last chat (last 2 years)
        if chats_from_users:
            last_chat_year = parse(chats_from_users[0].get('local_accepted')).year
            new_data_list.append({'operator': username, 'last_chat_year':last_chat_year})
        else:
            #The default year should be None
            new_data_list.append({'operator': username, 'last_chat_year':None})
        
        
    import pdb; pdb.set_trace() 
    df_operator = pd.DataFrame(new_data_list)

    

    #concatenate DF
    filename = "operator.xlsx"
    filepath = str(pathlib.PurePath(BASE_DIR, "tmp_file", filename))

    writer = pd.ExcelWriter(filepath, engine="xlsxwriter")
    df.to_excel(writer, index=False)
    writer.save()

    # return JsonResponse(context, safe=False)
    return render(request, "pivot.html", context)

@login_required
def download_excel_file_Operator_Assignment(request):

    filename = "operator.xlsx"
    filepath = str(pathlib.PurePath(BASE_DIR, "tmp_file", filename))

    from os import path

    if path.exists(filepath):
        print("file exist in : " + filepath)
        return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)
    else:
        assignments = helper_for_operator_assignments()

        df = pd.DataFrame(assignments)
        df["operator_copy"] = df["operator"]

        filename = "operator.xlsx"
        filepath = str(pathlib.PurePath(BASE_DIR, "tmp_file", filename))

        writer = pd.ExcelWriter(filepath, engine="xlsxwriter")
        df.to_excel(writer, index=False)
        writer.save()

    # TODO: Create this report using a cronjob
    return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)

@login_required
def get_unanswered_chats(request, *args, **kwargs):
    client = Client()
    today = datetime.today()
    chats = client.chats()
    last10days = today - timedelta(days=10)

    to_date = (
        str(last10days.year)
        + "-"
        + "{:02d}".format(last10days.month)
        + "-"
        + str(last10days.day)
    )
    all_chats = chats.list_day(
        year=today.year, month=today.month, day=today.day, to=to_date
    )
    unanswered = list()
    for chat in all_chats:
        if chat.get("operator") == None:
            unanswered.append(chat)

    # return JsonResponse(chats, safe=False)
    heatmap = [
        parse(chat.get("started")).replace(tzinfo=timezone.utc).timestamp()
        for chat in unanswered
    ]
    counter = {x: heatmap.count(x) for x in heatmap}
    heatmap_chats = json.dumps(counter)
    username = "Unanswered"
    current_year = "Last 10 days"

    unanswered = [Chats(chat) for chat in unanswered]
    return render(
        request,
        "results/chats.html",
        {
            "object_list": unanswered,
            "heatmap_chats": heatmap_chats,
            "username": username,
            "current_year": current_year,
        },
    )

@login_required
def pivotTableChatAnsweredByOperator(request):
    client = Client()
    chats = client.chats()

    today = datetime.today()
    yesterday = today - timedelta(days=3)

    chats = client.chats().list_day(year=2021, month=4, day=1, to="2021-05-18")[0:200]
    chats_initital = [Chats(chat) for chat in chats]

    chats_initital = [
        {
            "queue": s.queue,
            "school": s.school,
            "year": parse(s.started).year,
            "month": parse(s.started).strftime("%B"),
            "operator": s.operator,
        }
        for s in chats_initital
    ]

    operators = [chat.get("operator") for chat in chats_initital]
    queues = [chat.get("queue") for chat in chats]
    context = {"schools": chats_initital}
    return render(request, "pivot.html", context)

@login_required
def pivot_table_chats_per_schools(request):
    today = datetime.today()
    query = {
    "query": {
        "from": str(today.year)+"-06-19", 
        "to": str(today.year)+"-06-21"
        },
        "sort": [{"started": "descending"}],
    }
    client = Client()
    chats = client.api().post("v4", "/chat/_search", json=query)

    my_list = list()

    for chat in chats:
        accepted ='not answered'
        this_date = 'None'
        school = 'None'
        operator = 'None'
        if chat.get('accepted'):
            accepted = 'answered'
        if chat.get('queue'):
            school = find_school_by_queue_or_profile_name(chat.get('queue'))
        if chat.get('operator'):
            operator = chat.get('operator')
        try:
            if chat.get('started', 'None'):
                this_date = chat.get('started').split('T')[0]
        except:
            pass
        my_list.append({'accepted':accepted, 'this_date':this_date, 
                        'school':school, 'operator':operator, 'date':this_date,
                        'queue':chat.get('queue')})
    my_second_list = list()
    print(my_list)
    
    return render(request, "pivot/chats_per_school.html", {"object_list": my_list})



def write_report_to_file(filepath, content_of_the_report):
   with open(filepath, "w") as content:
      # Writing data to a file
      content.write(content_of_the_report)


def compress(file_names, zip_filename="RAWs.zip"):
    print("File Paths:")
    print(file_names)

    filepath = str(pathlib.PurePath(BASE_DIR, "tmp_file/report", zip_filename))


    # Select the compression mode ZIP_DEFLATED for compression
    # or zipfile.ZIP_STORED to just store the file
    compression = zipfile.ZIP_DEFLATED

    # create the zip file first parameter path/name, second mode
    zf = zipfile.ZipFile(zip_filename, mode="w")
    try:
        for file_name in file_names:
            # Add file to the zip file
            # first parameter file to zip, second filename in zip
            zf.write(filepath, compress_type=compression)

    except FileNotFoundError:
        print("An error occurred")
    finally:
        # Don't forget to close the file!
        zf.close()


def download_lh3_base_report(report_type):
   today = datetime.today()
   first_day_of_current_month = date.today().replace(day=1)
   last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)

   beginning_date =  date(today.year, (today.month -1), 1).strftime('%Y-%m-%d')
   ending_date = last_day_of_previous_month.strftime('%Y-%m-%d')

   current_time_now_in_string = datetime.now().strftime('--%H-%M-%S')

   client = lh3.api.Client()

   if report_type =="chats_per_operator":
      chats_per_operator = client.reports().chats_per_operator(start = beginning_date, end = ending_date)
      filepath = Path('tmp_file/report/chats_per_operator'+ "-from-" +beginning_date+ "-to-"+ending_date + current_time_now_in_string  +  ".csv")
      write_report_to_file(filepath, chats_per_operator)
   elif report_type =="chats_per_hour":
      chats_per_hour = client.reports().chats_per_hour(start = beginning_date, end = ending_date)
      filepath = Path('tmp_file/report/chats_per_hour'+ "-from-" +beginning_date+ "-to-"+ending_date + current_time_now_in_string  +".csv")
      write_report_to_file(filepath, chats_per_hour)
   elif report_type =="chats_per_month":
      chats_per_month = client.reports().chats_per_month(start = beginning_date, end = ending_date)
      filepath = Path('tmp_file/report/chats_per_month'+ "-from-" +beginning_date+ "-to-"+ending_date + current_time_now_in_string  + ".csv")
      write_report_to_file(filepath, chats_per_month)
   elif report_type =="chats_per_profile":
      chats_per_profile = client.reports().chats_per_profile(start = beginning_date, end = ending_date)
      filepath = Path('tmp_file/report/chats_per_profile'+ "-from-" +beginning_date+ "-to-"+ending_date + current_time_now_in_string  +  ".csv")
      write_report_to_file(filepath, chats_per_profile)
   elif report_type =="chats_per_queue":
      chats_per_queue = client.reports().chats_per_queue(start = beginning_date, end = ending_date)
      filepath = Path('tmp_file/report/chats_per_queue'+ "-from-" +beginning_date+ "-to-"+ending_date + current_time_now_in_string  +  ".csv")
      write_report_to_file(filepath, chats_per_queue)
   elif report_type =="chats_per_protocol":
      chats_per_protocol = client.reports().chats_per_protocol(start = beginning_date, end = ending_date)
      filepath = Path('tmp_file/report/chats_per_protocol'+ "-from-" +beginning_date+ "-to-"+ending_date + current_time_now_in_string  +  ".csv")
      write_report_to_file(filepath, chats_per_protocol)
   else:
      return False

   print(report_type)
   filepath.parent.mkdir(parents=True, exist_ok=True)  

   read_csv_file_df = pd.read_csv(filepath)
   #remove tempfile

   #write csv file again
   read_csv_file_df.to_csv(filepath, index=False)

   return filepath

#TODO MOVE everything under a folder; ZIP that folder instead and DELETE that folder

@login_required
def download_lh3_api_report(request):
    
    file_names = ["chats_per_operator", "chats_per_hour", "chats_per_month", 
    "chats_per_profile", "chats_per_queue", "chats_per_protocol"]

    compress(file_names)
    filenames = []
    for report in file_names:
        result = download_lh3_base_report(report)
        if result:
            filenames.append(result)
        if result == False:
            print("No report named {0} way in LibraryH3lp".format(report))

    
    shutil.make_archive(pathlib.PurePath(BASE_DIR, "tmp_file", "lh3_api_report"), 'zip', pathlib.PurePath(BASE_DIR, "tmp_file/report"))
    
    filepath = pathlib.PurePath(BASE_DIR, "tmp_file", "lh3_api_report.zip")

    zip_file = open(filepath, 'rb')

    response = HttpResponse(zip_file, content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename="lh3_api_report.zip"'

    #delete all .csv from report folder
    files = glob.glob("tmp_file/report/*.csv")
    for f in files:
        os.remove(f)

    return response


def find_reference_question_from_this_list_of_values(lh3ChatID, RQ_Postion):
    client = Client()
    transcript_metadata = client.one("chats", lh3ChatID).get()
    transcript = retrieve_transcript(transcript_metadata, lh3ChatID)

    try:
        transcript[RQ_Postion-1]
    except: 
        import pdb; pdb.set_trace()

    return transcript[RQ_Postion-1]

def extract_chat_text_content_from_this_transcript_message(message_metadata):
    message=message_metadata.get('message')
    soup = BeautifulSoup(message, "html.parser")
    div = soup.find("div")
    text_content = ' '.join(div.text.split(' ')[2::])
    
    return text_content

#TODO Create cronjob and store this file nightly
#TODO Use CELERY for (Background jobs)
@login_required
def download_list_of_reference_questions_in_MS_EXCEL_for_this_school_using_this_school_name(request, *args, **kwargs):
    
    client = Client()
    chats = client.chats()

    today = datetime.today()
    to_date = (
        str(today.year) + "-" + "{:02d}".format(today.month) + "-" + str(today.day)
    )
    chats = chats.list_day(
        year=today.year - 1, month=1, day=1, to=to_date
    )

    school = kwargs.get("school", None)
    queues = find_queues_from_a_school_name(school)
    filtered_chats = [chat for chat in chats if chat.get('queue') in queues]
    
    result_ids =chatReferenceQuestion.objects.filter(Q(queue_name__in=queues)).values_list('lh3ChatID', flat=True)

    reference_questions = list()

    school_name = None

    counter = 0
    #TODO - Do this with parallel programming
    for chat in filtered_chats:
        counter += 1
        lh3ChatID = chat.get('id')
        print("Searching for {0}".format(lh3ChatID))
        print("Number of chat left {0}-{1}={2}".format(len(filtered_chats), counter, len(filtered_chats)-counter))
        if lh3ChatID in result_ids:
            chat_found = (chatReferenceQuestion.objects.filter(lh3ChatID=lh3ChatID))[0]
            ref_question_found=chat_found.ref_question_found
            ref_question_position=chat_found.ref_question_position
            school_name = school #placeholder for FilenName
            message_metadata=find_reference_question_from_this_list_of_values(lh3ChatID=lh3ChatID, RQ_Postion=ref_question_position)
            chat_standalone_url=message_metadata.get('chat_standalone_url')
            this_chat_text_content = extract_chat_text_content_from_this_transcript_message(message_metadata)
        else:
            this_chat_text_content=None
            ref_question_found=None
            ref_question_position=None
            try:
                print("Chat queue: {0}".format(chat.get('queue') ))
                school=find_school_by_queue_or_profile_name(chat.get('queue'))
                queue_id = client.one("chats", lh3ChatID).get().get('queue_id')
            except:
                pass
                #import pdb; pdb.set_trace()
            chat_standalone_url= "https://ca.libraryh3lp.com/dashboard/queues/{0}/calls/REDACTED/{1}".format(
                        queue_id, lh3ChatID
                    )
        reference_questions.append(
            {
                "date": chat.get('started'),
                "guest":chat.get('guest'),
                "chat_standalone_url": chat_standalone_url,
                "Ref Question Found": ref_question_found,
                "Ref Question Postion (line/message)":ref_question_position,
                "operator":chat.get('operator'),
                "lh3ChatID":lh3ChatID,
                "Category": "",
                "Reference Question": this_chat_text_content, 
                "Reference Question (rephrased)": None, 
                "Category (CS or RQ)":None,
                "Custom Categorization":None,
                "Comment":None,
                "queue":chat.get('queue'),
                "school":school
            }

        )
    #@print(reference_questions)


    #Creating a Pandas DataFrame
    df = pd.DataFrame(reference_questions)

    filename = "reference_questions" + "_{0}".format(school_name) + ".xlsx"
    filepath = str(pathlib.PurePath(BASE_DIR, "tmp_file", filename))

    """
    #Table style
    css_alt_rows = 'background-color: seashell; color: black;'
    css_indexes = 'background-color: steelblue; color: white;'
    # Create file using the UTILS functions
    (df.style.apply(lambda col: np.where(col.index % 2, css_alt_rows, None)) # alternating rows
         .applymap_index(lambda _: css_indexes, axis=0) # row indexes (pandas 1.4.0+)
         .applymap_index(lambda _: css_indexes, axis=1) # col indexes (pandas 1.4.0+)
    ).to_excel(filepath, index=False, sheet_name="reference_questions", engine='openpyxl')
    """
    df.to_excel(filepath, index=False, sheet_name="reference_questions")

    # TODO: Create this report using a cronjob
    return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)


def get_download_list_of_all_reference_question(request, *args, **kwargs):
    """dowload the table

    Args:
        request (_type_): _description_

    Returns:
        _type_: _description_
    """
    #convert table to DataFrame
    
    df = pd.DataFrame(list(chatReferenceQuestion.objects.all().values()))
    df['created'] = df['created'].dt.tz_localize(None)
    df['modified'] = df['modified'].dt.tz_localize(None)
    df['operatorID'] = df['operatorID'].fillna(0.0).astype(int)

    #Filename
    today = datetime.today()
    filename = "all_reference_questions{0}.xlsx".format(datetime.now().strftime("%m-%d-%Y---%H-%M-%S"))
    filepath = str(pathlib.PurePath(BASE_DIR, "tmp_file", filename))
    df.to_excel(filepath, index=False, sheet_name="reference_questions")

    return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)



import requests, zipfile, io
import concurrent
import concurrent.futures 
urls = ["http://mlg.ucd.ie/files/datasets/multiview_data_20130124.zip",
   "http://mlg.ucd.ie/files/datasets/movielists_20130821.zip",
   "http://mlg.ucd.ie/files/datasets/bbcsport.zip",
   "http://mlg.ucd.ie/files/datasets/movielists_20130821.zip",
   "http://mlg.ucd.ie/files/datasets/3sources.zip"]

def download_zips(lh3ChatID):
    file_name = url.split("/")[-1]
    response = requests.get(url)
    sourceZip = zipfile.ZipFile(io.BytesIO(response.content))
    print("\n Downloaded {} ".format(file_name))
    sourceZip.extractall(filePath)
    print("extracted {} \n".format(file_name))
    sourceZip.close()

    with concurrent.futures.ThreadPoolExecutor() as exector : 
        exector.map(download_zips, urls)


def get_figsize_for_this_chart(number_of_distinct_year):

    if number_of_distinct_year == 1:
        figsize =(15,3)
    if number_of_distinct_year == 2:
        figsize =(15,6)
    elif number_of_distinct_year == 3:
        figsize =(21,10)
    elif number_of_distinct_year == 4:
        figsize =(28,18)
    elif number_of_distinct_year == 5:
        figsize =(34,18)
    else:
        figsize =(43,40)
    
    return figsize

def generate_calendar_image_from_df(df, username):
    #import pdb;pdb.set_trace()

    df = df[['started']]
    df['started'] = df['started'].astype('datetime64[ns]')
    df['started']=pd.to_datetime(df['started']).dt.strftime('%Y-%m-%d')
    df['Year'] = pd.DatetimeIndex(df['started']).year

    figsize = get_figsize_for_this_chart(len(df['Year'].unique()))

    del df['Year']

    value = df.value_counts()
    df = df.value_counts().rename_axis('dates').reset_index(name='value')

    df['dates']=pd.to_datetime(df['dates']).dt.strftime('%Y-%m-%d')
    df['dates'] = pd.to_datetime(df['dates'])
    df.index = pd.to_datetime(df['dates'])


    filename = ''
    fig, my_array = calplot.calplot(
        df['value'], 
        figsize=figsize,
        cmap='Spectral_r',
        )
    #fig.suptitle(username+"", fontsize=20)
    pylab.savefig('tmp_file/foo.png')
    del df


@login_required
def get_calplot_for_this_user(request, *args, **kwargs):
    username = kwargs.get("username", None)

    client = Client()
    #verify if operator has an LH3 account
    users = client.all('users').get_list()
    list_of_usernames = [operator['name'] for operator in users]
    if username in list_of_usernames:
        #if true use get LH3 chats for this user [use queries]
        today = datetime.today()
        query = {
            "query": {"operator": [username], "from":"2016-01-01", "to": str(today.year)+"-12-31"},
            "sort": [{"started": "descending"}],
        }
        chats_from_users, content_range = search_chats(client, query, chat_range=(0, 5000))
        
        df = pd.DataFrame(chats_from_users)

        generate_calendar_image_from_df(df, username)

        img = open('tmp_file/foo.png', 'rb')

        response = FileResponse(img, as_attachment=True, filename=username+"-calendar_heatmap.png")

        return response
    else:
        messages.success(request, "Invalid Username name" )
        return HttpResponseRedirect("/")
    #clean chats -> remove practice-queues
    #if not return message warning



@login_required
def get_calplot_for_the_service(request, *args, **kwargs):

    client = Client()

    today = datetime.today()
    chats = client.chats()
    last10days = today - timedelta(days=10)

    to_date = (
        str(2016)
        + "-"
        + "{:02d}".format(1)
        + "-"
        + str(8)
    )
    all_chats = chats.list_day(
        year=today.year, month=12, day=31, to=to_date
    )
    df = pd.DataFrame(all_chats)

    df = df[['started']]
    df['started'] = df['started'].astype('datetime64[ns]')
    df['started']=pd.to_datetime(df['started']).dt.strftime('%Y-%m-%d')
    df['Year'] = pd.DatetimeIndex(df['started']).year

    figsize = get_figsize_for_this_chart(len(df['Year'].unique()))

    del df['Year']

    value = df.value_counts()
    df = df.value_counts().rename_axis('dates').reset_index(name='value')

    df['dates']=pd.to_datetime(df['dates']).dt.strftime('%Y-%m-%d')
    df['dates'] = pd.to_datetime(df['dates'])
    df.index = pd.to_datetime(df['dates'])


    filename = ''
    fig, my_array = calplot.calplot(
        df['value'], 
        figsize=(28,20),
        cmap='Spectral_r',
        textformat='{:.0f}',
        )
    pylab.savefig('tmp_file/foo.png')
    del df

    img = open('tmp_file/foo.png', 'rb')

    response = FileResponse(img, as_attachment=True, filename="-Ask_a_Librarian__calendar_heatmap.png")

    return response

@login_required
def get_calplot_for_the_service_stratified(request, *args, **kwargs):

    client = Client()

    today = datetime.today()
    chats = client.chats()
    last10days = today - timedelta(days=10)

    to_date = (
        str(2016)
        + "-"
        + "{:02d}".format(1)
        + "-"
        + str(8)
    )
    all_chats = chats.list_day(
        year=today.year, month=12, day=31, to=to_date
    )
    df = pd.DataFrame(all_chats)

    df = df[['started']]
    df['started'] = df['started'].astype('datetime64[ns]')
    df['started']=pd.to_datetime(df['started']).dt.strftime('%Y-%m-%d')
    df['Year'] = pd.DatetimeIndex(df['started']).year

    figsize = get_figsize_for_this_chart(len(df['Year'].unique()))

    del df['Year']

    value = df.value_counts()
    df = df.value_counts().rename_axis('dates').reset_index(name='value')

    df['dates']=pd.to_datetime(df['dates']).dt.strftime('%Y-%m-%d')
    df['dates'] = pd.to_datetime(df['dates'])
    df.index = pd.to_datetime(df['dates'])


    filename = ''
    fig, my_array = calplot.calplot(
        df['value'], 
        figsize=(28,20),
        cmap='Paired',
        textformat='{:.0f}',
        )
    pylab.savefig('tmp_file/foo.png')
    del df

    img = open('tmp_file/foo.png', 'rb')

    response = FileResponse(img, as_attachment=True, filename="-Ask_a_Librarian__calendar_heatmap.png")

    return response

@login_required
def get_calplot_for_this_queue(request, *args, **kwargs):
    queue = kwargs.get("queue", None)

    client = Client()
    #verify if operator has an LH3 account
    users = client.all('users').get_list()
    list_of_usernames = [operator['name'] for operator in users]
    if username in list_of_usernames:
        #if true use get LH3 chats for this user [use queries]
        today = datetime.today()
        query = {
            "query": {"operator": [username], "from":"2016-01-01", "to": str(today.year)+"-12-31"},
            "sort": [{"started": "descending"}],
        }
        chats_from_users, content_range = search_chats(client, query, chat_range=(0, 5000))
        
        df = pd.DataFrame(chats_from_users)

        generate_calendar_image_from_df(df)

        img = open('tmp_file/queue.png', 'rb')

        response = FileResponse(img)

        return response
    else:
        messages.success(request, "Invalid Queue name" )
        return HttpResponseRedirect("/")
    #clean chats -> remove practice-queues
    #if not return message warning

@login_required
def get_calplot_for_this_school(request, *args, **kwargs):
    username = kwargs.get("school", None)

    client = Client()
    #verify if operator has an LH3 account
    users = client.all('users').get_list()
    list_of_usernames = [operator['name'] for operator in users]
    if username in list_of_usernames:
        #if true use get LH3 chats for this user [use queries]
        today = datetime.today()
        query = {
            "query": {"operator": [username], "from":"2016-01-01", "to": str(today.year)+"-12-31"},
            "sort": [{"started": "descending"}],
        }
        chats_from_users, content_range = search_chats(client, query, chat_range=(0, 5000))
        
        df = pd.DataFrame(chats_from_users)

        generate_calendar_image_from_df(df)

        img = open('tmp_file/school.png', 'rb')

        response = FileResponse(img)

        return response
    else:
        messages.success(request, "Invalid School name" )
        return HttpResponseRedirect("/")
    #clean chats -> remove practice-queues
    #if not return message warning