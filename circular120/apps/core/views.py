from django.http import HttpResponse

def home(request):
    return HttpResponse("Sistema funcionando correctamente ✅")

