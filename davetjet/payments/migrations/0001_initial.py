# Generated by Django 5.2.2 on 2025-06-05 04:57

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='USD', max_length=10)),
                ('payment_date', models.DateTimeField(auto_now_add=True)),
                ('payment_method', models.CharField(blank=True, max_length=50, null=True)),
                ('status', models.CharField(default='pending', max_length=20)),
                ('invoice_number', models.CharField(blank=True, max_length=50, null=True, unique=True)),
            ],
            options={
                'verbose_name': 'Payment',
                'verbose_name_plural': 'Payments',
                'ordering': ['payment_date'],
            },
        ),
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('billing_cycle', models.CharField(choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly', max_length=20)),
                ('features', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'verbose_name': 'Plan',
                'verbose_name_plural': 'Plans',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateTimeField(auto_now_add=True)),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('trial_start_date', models.DateTimeField(blank=True, null=True)),
                ('trial_end_date', models.DateTimeField(blank=True, null=True)),
                ('payment_method', models.CharField(blank=True, max_length=50, null=True)),
                ('billing_cycle', models.CharField(choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly', max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('currency', models.CharField(default='USD', max_length=10)),
                ('next_payment_date', models.DateTimeField(blank=True, null=True)),
                ('last_payment_date', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Subscription',
                'verbose_name_plural': 'Subscriptions',
                'ordering': ['user__username', 'start_date'],
            },
        ),
    ]
