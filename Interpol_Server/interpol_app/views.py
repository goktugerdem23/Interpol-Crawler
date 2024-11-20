from django.shortcuts import render
from .models import InterpolData
from django.views.generic import ListView


class ShowData(ListView):
    model = InterpolData
    template_name = "interpol_app/index.html"
    context_object_name = "wanted"
    paginate_by = 20
