import string

from django.utils.crypto import get_random_string

from celery import shared_task
from celery_once import AlreadyQueued


@shared_task(queue="celery")
def create_random_user_accounts(total):
    for i in range(total):
        username = "user_{}".format(get_random_string(10, string.ascii_letters))
        email = "{}@example.com".format(username)
        password = get_random_string(50)
        # User.objects.create_user(username=username, email=email, password=password)
        print("\t\tCreated User {0}\n".format(i))
    return "{} random users created with success!".format(total)


@shared_task
def crontab_for_list_of_user_activities():
    pass
