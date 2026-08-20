import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("puzzles", "0003_seed_starter_puzzles")]
    operations = [
        migrations.CreateModel(
            name="PuzzleCourse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=140, unique=True)),
                ("description", models.CharField(blank=True, max_length=300)),
                ("theme", models.CharField(db_index=True, max_length=80)),
                ("difficulty", models.CharField(choices=[("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced"), ("expert", "Expert")], db_index=True, default="beginner", max_length=16)),
                ("is_published", models.BooleanField(db_index=True, default=True)),
            ],
            options={"ordering": ["difficulty", "title"]},
        ),
        migrations.CreateModel(
            name="PuzzleCourseItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveSmallIntegerField(default=1)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="puzzles.puzzlecourse")),
                ("puzzle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="course_items", to="puzzles.puzzle")),
            ],
            options={"ordering": ["position", "id"]},
        ),
        migrations.AddField(model_name="puzzlecourse", name="puzzles", field=models.ManyToManyField(related_name="courses", through="puzzles.PuzzleCourseItem", to="puzzles.puzzle")),
        migrations.AddConstraint(model_name="puzzlecourseitem", constraint=models.UniqueConstraint(fields=("course", "puzzle"), name="puzzle_course_unique_puzzle")),
        migrations.AddConstraint(model_name="puzzlecourseitem", constraint=models.UniqueConstraint(fields=("course", "position"), name="puzzle_course_unique_position")),
    ]
