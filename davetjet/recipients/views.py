from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
import pandas as pd
from io import BytesIO, StringIO
from .models import Recipient

class RecipientTestView(TemplateView):
    template_name = 'recipients/test.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class CreateRecipientView(CreateView):
    model = Recipient
    template_name = 'recipients/add_new.html'
    fields = ['name', 'email']
    success_url = reverse_lazy('recipients:add_new')

    def form_valid(self, form):
        form.instance.save()
        print("Recipient created successfully")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Recipient'
        return context

class AddFromFileView(View):
    template_name = 'recipients/test.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        recipients = []

        if not uploaded_file:
            return render(request, self.template_name, {'error': 'No file uploaded.'})


        try:
            if uploaded_file.name.endswith('.csv'):
              data = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(('.xls', '.xlsx')):
              data = pd.read_excel(uploaded_file)
            else:
               return render(request, self.template_name, {'error': 'Unsupported file format.'})

            # Expecting columns: 'name' and 'email'
            for _, row in data.iterrows():
              name = row.get('name')
              email = row.get('email')
              if pd.notna(name) and pd.notna(email):
                recipients.append({'name': name, 'email': email})
                Recipient.objects.create(name=name, email=email).save()
            if not recipients:
                return render(request, self.template_name, {'error': 'No valid recipients found in the file.'})

        except Exception as e:
            return render(request, self.template_name, {'error': f'Error processing file: {e}'})

        return render(request, self.template_name, {
            'message': f'File processed successfully. {len(recipients)} recipients added.',
            'recipients': recipients
        })
