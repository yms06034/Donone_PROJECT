# Generated by Django 3.2.3 on 2023-01-31 10:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('don_home', '0005_ablyproductinfo_ablysalesinfo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='registrationDate',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='ablysalesinfo',
            name='paymentDate',
            field=models.CharField(max_length=50),
        ),
    ]