# -*- coding: utf-8 -*-
import json

# Test package & Utils
from django.test import TestCase
from django.urls import reverse

import pytest
from dashboard.views.assignee import get_assignee_for_this_queue
from lh3.api import *

""" 
==================
URLS
==================

get_assignee_for_this_queue
"""

# Fixture package


pytestmark = pytest.mark.django_db


class Unit_test(TestCase):
    @pytest.mark.skip(reason="2022-10-24")
    def test_view_assignee(self):
        assert "p" in "pass"
