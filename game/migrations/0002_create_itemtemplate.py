from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('game', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ItemTemplate',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('category', models.CharField(max_length=100)),
                ('cost', models.IntegerField()),
                ('description', models.TextField()),
                ('sprite_path', models.CharField(max_length=255)),
                ('api_url', models.URLField()),
            ],
        ),
    ]
