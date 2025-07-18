from django.db import models
from django.contrib.auth.models import AbstractUser

class users(AbstractUser):
    username = models.CharField(max_length=52, primary_key=True)
    firstname = models.CharField(max_length=52)
    lastname = models.CharField(max_length=52)
    email = models.EmailField(unique=True)

    datejoined = models.DateTimeField(auto_now_add=True) 
    balance = models.FloatField(default=100000.0)

    stockbuy = models.JSONField(default=dict)
    stocksold = models.JSONField(default=dict)
    watchlist = models.JSONField(default=list)
    cache = models.JSONField(default=list)

    def __str__(self):
        return self.username