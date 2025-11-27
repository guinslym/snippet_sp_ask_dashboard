import pytest
from django.urls import reverse
from django.test import Client
from unittest.mock import patch
from django.contrib.auth.models import User


# Fixture to simulate a logged-in user
@pytest.fixture
def authenticated_user(db):
    user = User.objects.create_user(username="testuser", password="12345")
    client = Client()
    client.login(username="testuser", password="12345")
    return client


# Mocking query_for_get_transcript to avoid real database/API calls
@patch("dashboard.views.transcript.query_for_get_transcript")
def test_get_transcript_view(mock_query_for_get_transcript, authenticated_user):
    # Setup mock data
    mock_query_for_get_transcript.return_value = {
        "object_list": [
            {
                "chat_id": 1,
                "started": "2024-10-23T10:00:00",
                "guest": "sdfger",  # Ensure guest_id is present
                "queue_name": "test_queue",
                "operator": "test_operator",
            }
        ],
        "queue_name": "test_queue",
        "started_date": "2024-10-23",
        "guest": "sdfger",  # Ensure guest_id is present
        "chat_id": 1,
        "operator": "test_operator",
    }

    # Simulate a request to the get_transcript view
    url = reverse("get_chat_transcript", kwargs={"chat_id": 1})
    response = authenticated_user.get(url)

    # Assert the response is 200 OK
    assert response.status_code == 200
    assert "test_queue".upper() in response.content.decode()
