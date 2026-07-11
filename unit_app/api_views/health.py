from .common_imports import *

from django.shortcuts import render
from django.http import HttpResponse

def health(request):
    return HttpResponse("Backend is healthy and running!")