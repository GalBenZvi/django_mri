# Generated by Django 3.0.6 on 2020-07-14 05:04

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_extensions.db.fields
import django_mri.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ("django_mri", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="nifti", options={"ordering": ("-id",), "verbose_name": "NIfTI"},
        ),
        migrations.AddField(
            model_name="sequencetype",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="created",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="sequencetype",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(
                auto_now=True, verbose_name="modified"
            ),
        ),
        migrations.CreateModel(
            name="SequenceTypeDefinition",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name="modified"
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="title")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="description"),
                ),
                (
                    "scanning_sequence",
                    django_mri.models.fields.ChoiceArrayField(
                        base_field=models.CharField(
                            choices=[
                                ("SE", "Spin Echo"),
                                ("IR", "Inversion Recovery"),
                                ("GR", "Gradient Recalled"),
                                ("EP", "Echo Planar"),
                                ("RM", "Research Mode"),
                            ],
                            max_length=2,
                        ),
                        blank=True,
                        null=True,
                        size=5,
                    ),
                ),
                (
                    "sequence_variant",
                    django_mri.models.fields.ChoiceArrayField(
                        base_field=models.CharField(
                            choices=[
                                ("SK", "Segmented k-Space"),
                                ("MTC", "Magnetization Transfer Contrast"),
                                ("SS", "Steady State"),
                                ("TRSS", "Time Reversed Steady State"),
                                ("SP", "Spoiled"),
                                ("MP", "MAG Prepared"),
                                ("OSP", "Oversampling Phase"),
                                ("NONE", "None"),
                            ],
                            max_length=4,
                        ),
                        blank=True,
                        null=True,
                        size=None,
                    ),
                ),
                (
                    "sequence_type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sequence_definition_set",
                        to="django_mri.SequenceType",
                    ),
                ),
            ],
            options={
                "ordering": ("title",),
                "unique_together": {("scanning_sequence", "sequence_variant")},
            },
        ),
    ]