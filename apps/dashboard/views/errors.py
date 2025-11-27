# standard library
import pathlib
from pprint import pprint as print
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required

# installed package
from lh3.api import *
from dateutil.parser import parse
from django.http import JsonResponse
from django.http import FileResponse
from django.views.decorators.csrf import csrf_exempt
import pandas as pd

from core.settings.base import BASE_DIR

from django.shortcuts import render


def page_not_found(request, exception, template_name="404.html"):
    context = {"foo": "bar"}
    return render(request, "404.html", context)


def lh3_connection_error(request):
    context = {"foo": "bar"}
    return render(request, "errors/lh3_connection_error.html", context)


def error_404(request, exception):
    return render(request, "404.html")


def handler404(request, *args, **argv):
    """
    response = render('404.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 404
    return response
    """
    pass
