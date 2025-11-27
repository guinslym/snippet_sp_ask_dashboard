# standard library
import pathlib
from datetime import datetime, timedelta
from pprint import pprint as print
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

import pandas as pd
from apps.dashboard.forms import ChatSearchForm, ReferenceQuestionUploadForm
from apps.dashboard.models import chatReferenceQuestion
from sp_ask_school import (
    find_queues_from_a_school_name,
    find_school_by_operator_suffix,
    find_school_by_queue_or_profile_name,
)
from apps.dashboard.utils.utils import (
    Chats,
    retrieve_transcript,
    search_chats,
    soft_anonimyzation,
)
from apps.dashboard.views.queries.q_transcript import (
    query_for_add_this_as_a_reference_question,
    query_for_download_transcript_in_html,
    query_for_get_transcript,
    query_for_search_transcript_with_in_multifield_form,
    query_for_search_transcript_with_this_ip_address,
    query_for_search_transcript_with_this_keyword,
    query_for_transcript_that_contains_file_transfer,
    query_for_transcript_that_was_transferred,
)
from dateutil.parser import parse
from lh3.api import *
from core.settings.base import BASE_DIR

from django.http import (
    FileResponse,
    Http404,
    HttpResponseRedirect,
    JsonResponse,
    HttpResponse,
)


@login_required
def get_transcript(request, *args, **kwargs):
    chat_id = int(kwargs.get("chat_id", None))
    result = query_for_get_transcript(chat_id)

    # Ensure queue_name is present in result
    queue_name = result["object_list"][0].get("queue_name", None)
    result["queue_name"] = queue_name

    return render(
        request,
        "transcript/transcript.html",
        result,
    )


@login_required
def add_this_as_a_reference_question(request, *args, **kwargs):
    chat_id = int(kwargs.get("chat_id", None))
    position = int(kwargs.get("message_position", None))

    added_in_db = query_for_add_this_as_a_reference_question(chat_id, position)

    if added_in_db:
        print({"object": "created"})
        result = {"object": "created"}
    else:
        print({"object": "not created"})
        result = {"object": "not created"}

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(result, safe=False)
    else:
        result = query_for_get_transcript(chat_id)
        return render(
            request,
            "transcript/transcript.html",
            result,
        )
    # return JsonResponse(result, safe=False)


@login_required
@csrf_exempt
def search_transcript_that_was_transferred(request, *args, **kwargs):
    chats = query_for_transcript_that_was_transferred(results=(0, 100))
    return render(
        request,
        "results/chat_transferred.html",
        {"object_list": chats, "guest_id": "fake GuestID"},
    )


@login_required
@csrf_exempt
def search_transcript_that_contains_file_transfer(request, *args, **kwargs):
    chats = query_for_transcript_that_contains_file_transfer(results=(0, 100))
    return render(
        request,
        "results/chat_with_file_transfer.html",
        {"object_list": chats, "guest_id": "fake GuestID"},
    )


@login_required
def download_transcript_in_html(request, *args, **kwargs):
    chat_id = int(kwargs.get("chat_id", None))
    transcript_in_html = query_for_download_transcript_in_html(chat_id)

    filename = "last-transcript-downloaded.html"
    filepath = str(pathlib.PurePath(BASE_DIR, "tmp_file", filename))

    try:
        with open(filepath, "w") as file:
            file.write(" ".join(transcript_in_html))
    except:
        print("error creating transcript file")

    return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)


@login_required
@csrf_exempt
def search_transcript_with_this_keyword(request, *args, **kwargs):
    search_string = request.POST.get("in_transcript", None)
    chats = None
    if search_string:
        chats = query_for_search_transcript_with_this_keyword(
            search_string, results=(0, 500)
        )
        return render(
            request,
            "results/search_transcript.html",
            {"object_list": chats, "guest_id": "This keyword {}".format(search_string)},
        )
    return render(request, "results/search_transcript.html", {"object_list": None})


@login_required
@csrf_exempt
def search_transcript_with_this_ip_address(request, *args, **kwargs):
    ip_address = request.POST.get("ip_address", None)
    chats = None
    if ip_address:
        chats = query_for_search_transcript_with_this_ip_address(
            ip_address, results=(0, 500)
        )
        return render(
            request,
            "results/search_transcript_with_ip_address.html",
            {"object_list": chats, "guest_id": "This IP address {}".format(ip_address)},
        )
    return render(
        request, "results/search_transcript_with_ip_address.html", {"object_list": None}
    )


@login_required
def search_transcript_with_in_multifield_form(request):
    if request.method == "POST":
        query = request.POST.get("in_transcript", None)
        form = ChatSearchForm(request.POST)
        if form.is_valid():
            pass
            print("*" * 100)
            print("FORM valid")
            print("*" * 100)

            chats = query_for_search_transcript_with_in_multifield_form(
                request, results=(0, 1000)
            )
            ref_questions = chatReferenceQuestion.objects.all().values_list("lh3ChatID", flat=True)
            


            return render(
                request,
                "results/search_transcript_using_a_multiform.html",
                {
                    "object_list": chats,
                    "guest_id": "result",
                    "form": ChatSearchForm(),
                    "query": query,
                    "ref_questions": ref_questions,  # Add this line
                },
            )
    else:
        form = ChatSearchForm()
    return render(
        request, "results/search_transcript_using_a_multiform.html", {"form": form}
    )


def handle_uploaded_file(my_ref_question_file):
    df = pd.read_excel(my_ref_question_file)
    counter = 0
    for indice in df.itertuples():
        print(
            "Reading File \t ID: {0}, QueueId:{1}".format(
                df["lh3ChatID"][counter], df["queueID"][counter]
            )
        )
        if chatReferenceQuestion.objects.filter(lh3ChatID=df["lh3ChatID"][counter]):
            pass
        else:
            chatReferenceQuestion.objects.create(
                lh3ChatID=df["lh3ChatID"][counter],
                ref_question_found=int(df["ref_question_found"][counter]),
                ref_question_position=df["ref_question_position"][counter],
                operatorID=df["operatorID"][counter],
                queueID=df["queueID"][counter],
                queue_name=df["queue_name"][counter],
            )
        counter += 1


@login_required
def viewUploadReferenceFile(request):
    # Handle file upload
    # import pdb; pdb.set_trace()
    if request.method == "POST":
        import pdb

        pdb.set_trace()
        form = ReferenceQuestionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            print("is_valid")

            df = handle_uploaded_file(request.FILES["docfile"])
            return HttpResponseRedirect("/")
    else:
        form = ReferenceQuestionUploadForm()
    return render(request, "transcript/upload_reference_question.html", {"form": form})

    dir(request.FILES["docfile"])
