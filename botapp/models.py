from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class BotUser(AbstractUser):
    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    username = models.CharField(unique=True, max_length=100, blank=True, null=True, verbose_name="Username")
    full_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Full name")
    is_authorized = models.BooleanField(default=False, verbose_name="Authorized")
    favorite_videos = models.ManyToManyField('Video', blank=True, related_name='liked_by_user')
    favorite_movies = models.ManyToManyField('Movie', blank=True, related_name='liked_by_user')


    def __str__(self):
        return self.username or str(self.telegram_id)

    @property
    def is_authenticated(self):
        return self.is_authorized

class Video(models.Model):
    title = models.CharField(max_length=200, verbose_name="Video title")
    url = models.URLField(max_length=500, verbose_name="Video URL")

    def __str__(self):
        return self.title

class Movie(models.Model):
    title = models.CharField(max_length=200, verbose_name="Movie title")
    url = models.URLField(max_length=500, verbose_name="Movie URL")
    def __str__(self):
        return self.title



# ForeignKey, OneToOne, ManyToMany    https://docs.djangoproject.com/en/5.1/topics/db/examples/many_to_many/