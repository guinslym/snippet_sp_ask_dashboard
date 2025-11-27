from django.db import models
from django.urls import reverse, reverse_lazy

from model_utils import Choices
from model_utils.models import TimeStampedModel


# TODO There is a table dailyOffered in the Databasse (sqlite) that need to be delete
class lh3DailyOffered(TimeStampedModel):
    id = models.AutoField(primary_key=True)
    username_id = models.CharField(max_length=50, blank=True, null=True)
    hour = models.PositiveIntegerField(blank=True, null=True)
    num_offered = models.PositiveIntegerField(blank=True, null=True)
    num_answered = models.PositiveIntegerField(blank=True, null=True)
    offered_date = models.DateField(blank=True, null=True, default="")

    def __str__(self):
        return str(self.username)

    def __repr__(self):
        return "DB Table: <dailyOffered> : \n offered_date: {0}\n username: {1}\n hour:{2}\n num_offered:{3}\num_answered:{4}\n".format(
            self.offered_date,
            self.username,
            self.hour,
            self.num_offered,
            self.num_answered,
            "{:%Y-%m-%d}".format(self.offered_date),
        )

    def get_absolute_url(self):
        return reverse("dailyOffered_edit", kwargs={"pk": self.pk})

    class Meta:
        indexes = [
            models.Index(fields=["offered_date", "id"]),
        ]


""""
#Dumb data

import random 
import time
start_time = time.time()
counter = 0

for i in range(0, 30000):
    counter +=1
    if counter % 100 == 0:
        print("{0} in {1} seconds".format(str(counter), int(time.time() - start_time)))
    chatReferenceQuestion.objects.create(
        lh3ChatID=random.randint(35000, 3500000),
        ref_question_found=random.randint(0, 1),
        ref_question_position=random.randint(0, 35),
        operatorID=random.randint(725, 3450),
        queueID=random.randint(0, 43),
        queue_name="toronto-st-george"
    )
print("--- %s seconds ---" % int(time.time() - start_time))


"""


class chatReferenceQuestion(TimeStampedModel):
    id = models.AutoField(primary_key=True)
    lh3ChatID = models.PositiveIntegerField(blank=True, null=True)
    # lh3guestID = models.CharField(max_length=50, blank=True, null=True)
    ref_question_found = models.BooleanField(blank=True, null=True, default=False)
    ref_question_position = models.PositiveIntegerField(blank=True, null=True)
    operatorID = models.PositiveIntegerField(blank=True, null=True)
    # operator_username = models.CharField(max_length=50, blank=True, null=True)
    queueID = models.PositiveIntegerField(blank=True, null=True)
    queue_name = models.CharField(max_length=50, blank=True, null=True)
    # school = models.CharField(max_length=50, blank=True, null=True)
    # started_date = models.DateTimeField(blank=True, null=True, default='')

    def __str__(self):
        return str(self.lh3ChatID)

    def __repr__(self):
        return "DB Table: <chatReferenceQuestion> : \n lh3ChatID: {0}\n operatorID: {1}\n ref_question_position:{2}\n".format(
            self.lh3ChatID,
            self.operatorID,
            self.ref_question_position,
        )

    def get_absolute_url(self):
        return reverse("chat_ref_edit", kwargs={"pk": self.pk})

    class Meta:
        indexes = [
            models.Index(fields=["lh3ChatID", "queueID"]),
        ]


class ChatLightAssessment(TimeStampedModel):
    STATUS = Choices(
        ("Canned Message", ("Canned Message")),
        ("LibraryH3lp Issue", ("LibraryH3lp Issue")),
        ("Library Website Issue", ("Library Website Issue")),
        ("Training", ("Training")),
        ("Unanswered", ("Unanswered")),
        ("Mentee", ("Mentee")),
        ("Ask Chat Policy", ("Ask Chat Policy")),
        ("Message to Operator", ("Message to Operator")),
        ("Transcript Review Commitee", ("Transcript Review Commitee")),
    )

    status = models.CharField(
        max_length=32,
        choices=STATUS,
    )

    id = models.AutoField(primary_key=True)
    lh3ChatID = models.PositiveIntegerField(blank=True, null=True)
    categories = models.BooleanField(blank=True, null=True, default=False)
    to_follow_up = models.BooleanField(blank=True, null=True, default=False)
    comment = models.TextField(blank=True, null=True)
    operatorID = models.PositiveIntegerField(blank=True, null=True)
    queueID = models.PositiveIntegerField(blank=True, null=True)
    school = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.lh3ChatID

    def get_absolute_url(self):
        return reverse("Chat_edit", kwargs={"pk": self.pk})

    class Meta:
        ordering = ("-lh3ChatID",)
        indexes = [
            models.Index(fields=["lh3ChatID", "queueID"]),
        ]


class flag(TimeStampedModel):
    id = models.AutoField(primary_key=True)
    lh3ChatID = models.PositiveIntegerField(blank=True, null=True)
    flag = models.BooleanField(blank=True, null=True, default=True)

    def __str__(self):
        return self.lh3ChatID

    class Meta:
        ordering = ("-lh3ChatID",)
        indexes = [
            models.Index(fields=["lh3ChatID"]),
        ]
