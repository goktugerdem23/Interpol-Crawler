from django.urls import path
from . import views

app_name = 'interpol_app'

urlpatterns = [
   path("",views.ShowData.as_view(),name="showdata"),
   path("search/",views.search,name="search")
]