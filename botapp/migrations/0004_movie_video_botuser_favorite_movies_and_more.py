# Generated by Django 5.1.2 on 2024-10-29 15:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('botapp', '0003_remove_botuser_favorite_movie_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Movie',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Movie title')),
                ('url', models.URLField(max_length=500, verbose_name='Movie URL')),
            ],
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Video title')),
                ('url', models.URLField(max_length=500, verbose_name='Video URL')),
            ],
        ),
        migrations.AddField(
            model_name='botuser',
            name='favorite_movies',
            field=models.ManyToManyField(blank=True, related_name='liked_by_user', to='botapp.movie'),
        ),
        migrations.AddField(
            model_name='botuser',
            name='favorite_videos',
            field=models.ManyToManyField(blank=True, related_name='liked_by_user', to='botapp.video'),
        ),
    ]
