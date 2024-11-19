from django.db import models


class InterpolData(models.Model):
    name = models.CharField(max_length=255)
    age = models.CharField(max_length=255)
    nationality = models.CharField(max_length=100)
    img_url = models.URLField(max_length=500)
   