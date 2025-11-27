from apps.dashboard.models import ChatLightAssessment
from django.forms import ModelForm

from lh3.api import *
from django.http import Http404, HttpResponseRedirect

from django.db.models.fields import BLANK_CHOICE_DASH
from django.urls import reverse

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

# https://simpleisbetterthancomplex.com/tutorial/2018/11/28/advanced-form-rendering-with-django-crispy-forms.html
from apps.dashboard.utils.ask_schools import sp_ask_school_dict


from apps.dashboard.utils.utils import (
    get_lh3_client_connection,
)


from lh3.api import Client


def try_to_connect_to_lh3():
    client = get_lh3_client_connection()
    if client == False:
        return HttpResponseRedirect(reverse("lh3_connection_error"))
    else:
        return client


client = try_to_connect_to_lh3()

client.set_options(version="v1")

QUEUES = [item.get("school").get("queues") for item in sp_ask_school_dict]


def turn_operator_list_to_tuple():
    OPERATORS = list()
    all_operators = client.all("users").get_list()
    counter = 1
    for operator in all_operators:
        OPERATORS.append((str(counter), operator.get("name")))
        counter += 1
    return OPERATORS


def turn_school_list_to_tuple():
    SCHOOLS = list()
    list_of_school = [
        item.get("school").get("short_name") for item in sp_ask_school_dict
    ]
    list_of_school.sort()
    list_of_school + BLANK_CHOICE_DASH
    counter = 1
    for item in sp_ask_school_dict:
        SCHOOLS.append((str(counter), item.get("school").get("short_name")))
        counter += 1
    return SCHOOLS


OPERATORS = turn_operator_list_to_tuple()
SCHOOLS = turn_school_list_to_tuple()


class ChatSearchForm(forms.Form):
    guest_id = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Type guest ID"}), required=False
    )
    in_transcript = forms.CharField(
        widget=forms.TextInput(
            attrs={"placeholder": "Enter keyword/'part of sentence'"}
        ),
        required=False,
    )
    ip_address = forms.CharField(
        widget=forms.TextInput(
            attrs={"placeholder": "Type in the full IP address"},
        ),
        required=False,
    )
    # operator = forms.ChoiceField(choices=(OPERATORS))
    # school = forms.ChoiceField(choices=(SCHOOLS))
    # https://stackoverflow.com/a/41876821
    start_date = forms.DateTimeField(
        input_formats=["%d/%m/%Y %H:%M"],
        widget=forms.TextInput(attrs={"class": "start_date"}),
        required=False,
    )
    end_date = forms.DateTimeField(
        input_formats=["%d/%m/%Y %H:%M"],
        widget=forms.TextInput(attrs={"class": "end_date"}),
        required=False,
    )
    operator = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Operator username"}),
        required=False,
    )
    # school = forms.CharField(widget=forms.TextInput(attrs={'placeholder': "School name"}),required=False)
    school = forms.ChoiceField(choices=[], label="School", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # import pdb; pdb.set_trace()
        # Add a placeholder option at the beginning of the choices
        placeholder_option = [("", "Select a school")]

        # Populate the school choices dynamically here, for example:
        schools = [
            (
                school_dict["school"].get("short_name"),
                school_dict["school"].get("full_name"),
            )
            for school_dict in sp_ask_school_dict
        ]

        # Combine the placeholder option with the dynamic choices
        self.fields["school"].choices = placeholder_option + schools

        self.helper = FormHelper()
        self.helper.layout = Layout(
            "guest_id",
            "in_transcript",
            "ip_address",
            Row(
                Column("start_date", css_class="form-group col-md-6 mb-0 start_date"),
                Column("end_date", css_class="form-group col-md-6 mb-0 end_date"),
                css_class="form-row",
            ),
            Row(
                Column("operator", css_class="form-group col-md-6 mb-0 operator"),
                Column("school", css_class="form-group col-md-6 mb-0 school"),
                css_class="form-row",
            ),
            Submit("submit", "Submit", css_class="btn btn-primary"),
        )


class ReferenceQuestionUploadForm(forms.Form):
    docfile = forms.FileField(
        label="Select a file", help_text="max. 42 megabytes", required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
