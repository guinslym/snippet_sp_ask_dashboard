from django.http import JsonResponse
from django.shortcuts import render

from apps.dashboard.utils import utils
from lh3.api import *


def get_assignee_for_this_queue(request, *args, **kwargs):
    """Return the list of operator Assigned to that queue

    Args:
        request Request: HTTP Request header

    Returns:
        list: list of dict (i.e.  [{'id': 31920,
                                    'name': 'colleen_brk',
                                    'show': 'unavailable',
                                    'enabled': True},...])
    """
    client = Client()
    queue = kwargs.get("queue_name", None)
    assignments = client.find_queue_by_name(queue).all("operators").get_list()

    return render(request, "index.html", {"object_list": assignments})
