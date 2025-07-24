from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from .models import Project

class ProjectsTestView(TemplateView):
    template_name = 'projects/test.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message'] = 'This is a test view for projects.'
        return context

class CreateProjectView(CreateView):
    model = Project
    template_name = 'projects/test.html'
    fields = ['name', 'description']
    success_url = reverse_lazy('projects:test')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.is_active = True
        form.instance.save()
        print("Project created successfully")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Project'
        return context