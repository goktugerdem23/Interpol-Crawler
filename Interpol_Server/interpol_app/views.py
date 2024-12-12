from django.shortcuts import render
from .models import InterpolData
from django.views.generic import ListView
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.core.paginator import Paginator

class ShowData(ListView):
    model = InterpolData
    template_name = "interpol_app/index.html"
    context_object_name = "wanted"
    paginate_by = 20



def search(request):
    query = request.GET.get('q')
    results = []
    if query:
        search_vector = SearchVector('name','age','nationality','img_url')
        search_query = SearchQuery(query)
        results =  InterpolData.objects.annotate(search=search_vector).filter(search = search_query)
    
        paginator = Paginator(results,20)
        page_number = request.GET.get('page')
        page_obj  = paginator.get_page(page_number)
        
    return render(request, 'interpol_app/search.html', {'page_obj': page_obj, 'query': query})
    