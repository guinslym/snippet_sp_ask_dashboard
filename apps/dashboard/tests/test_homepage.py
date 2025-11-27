import pytest
from django.urls import reverse
from django.test import Client
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User


# Fixture to simulate a logged-in user
@pytest.fixture
def authenticated_user(db):
    user = User.objects.create_user(username="testuser", password="12345")
    client = Client()
    client.login(username="testuser", password="12345")
    return client


# Mocking get_lh3_client_connection to avoid real API calls
@patch("dashboard.views.homepage.get_lh3_client_connection")
@patch("dashboard.views.homepage.query_for_homepage_recent_chats")
@patch("dashboard.views.homepage.soft_anonimyzation")
def test_homepage_view(
    mock_soft_anonimyzation,
    mock_query_for_homepage_recent_chats,
    mock_lh3_client_connection,
    authenticated_user,
):
    # Setup mock client object with necessary methods
    mock_client = MagicMock()
    mock_client.set_options.return_value = None
    mock_client.all.return_value.get_list.return_value = [
        {"name": "test_operator", "show": "available"}
    ]
    mock_lh3_client_connection.return_value = mock_client  # Use the mock client

    # Ensure the mock chat data has valid date strings
    mock_query_for_homepage_recent_chats.return_value = [
        {
            "id": 1,
            "started": "2024-10-23T10:00:00",  # Valid date string
            "ended": "2024-10-23T10:30:00",
            "guest": "guest@example.com",
            "operator": "test_operator",
            "queue": "test_queue",
        }
    ]

    mock_soft_anonimyzation.return_value = [
        {
            "id": 1,
            "started": "2024-10-23T10:00:00",  # Valid date string
            "ended": "2024-10-23T10:30:00",
            "guest": "guest@example.com",
            "operator": "test_operator",
            "queue": "test_queue",
        }
    ]

    # Simulate a request to the homepage
    url = reverse("homepage")  # Assuming 'homepage' is the name of the URL pattern
    response = authenticated_user.get(url)

    # Assert the response is 200 OK
    assert response.status_code == 200

    # Check if the correct template is used
    assert "homepage.html" in [t.name for t in response.templates]

    # Check if the expected context data is present
    assert "object_list" in response.context
    assert (
        response.context["object_list"][0].chat_id == 1
    )  # Assuming the chat has been anonymized and returned properly
