from django.urls import path
from .views import Scrapper

urlpatterns = [
    path('scrapper/', Scrapper.as_view(), name='scrapper'),
]
