from django.db import models


class InterpolData(models.Model):
    family_name = models.CharField(max_length=50,null=True)
    forename = models.CharField(max_length=50,null=True)
    age = models.IntegerField()
    nationality = models.CharField(max_length=50)
    img_url = models.URLField(max_length=100)
   