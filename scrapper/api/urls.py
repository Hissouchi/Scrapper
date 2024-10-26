from django.urls import path
from .views import Sprapper

urlpatterns = [
    path('scrapper/', Sprapper.as_view(), name='scrapper'),
]
