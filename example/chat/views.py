"""Views for the chat example app."""

from django.shortcuts import render


def index(request):
    return render(request, "chat/index.html")
