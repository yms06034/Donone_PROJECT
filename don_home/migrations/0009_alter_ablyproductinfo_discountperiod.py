# Generated by Django 3.2.3 on 2023-01-31 10:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('don_home', '0008_auto_20230131_1939'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='discountPeriod',
            field=models.CharField(max_length=100),
        ),
    ]