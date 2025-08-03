from django.http import HttpResponse
import pandas as pd 
from .models import Recipient
from projects.models import Project
import sys

def process_recipient_file(uploaded_file, project=None):
    print("Processing file:", uploaded_file.name)
    if not uploaded_file:
        raise ValueError("No file uploaded.")

    if uploaded_file.name.endswith('.csv'):
        data = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(('.xls', '.xlsx')):
        data = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Unsupported file format.")

    recipients = []
    for _, row in data.iterrows():
        name = row.get('name')
        email = row.get('email')
        if pd.notna(name) and pd.notna(email):
            if not isinstance(name, str) or not isinstance(email, str):
                raise ValueError("Invalid data format. 'name' and 'email' must be strings.")
            
            if not email.strip():
                raise ValueError("Email cannot be empty.")
            
            if not name.strip():
                raise ValueError("Name cannot be empty.")
            
            if Recipient.objects.filter(email=email).exists():
                continue

            recipient = Recipient(name=name, email=email)
            recipient.save()
            if project:
                try:
                    recipient.project.add(project)
                except Exception as e:
                    print(f"Error adding recipient to project: {e}", file=sys.stderr)
                # recipient.project.add
            recipient.save()
            recipients.append(recipient)

    if not recipients:
        raise ValueError("No valid recipients found in the file.")

    return recipients