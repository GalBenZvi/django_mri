import factory

from django.core.exceptions import ValidationError
from django.db.models import signals
from django.test import TestCase
from django_dicom.models import Image, Series
from django_mri.models import Scan, NIfTI, Session
from django_mri.models.sequence_type import SequenceType
from pathlib import Path
from datetime import datetime
from tests.factories import SubjectFactory
from tests.models import Subject
from tests.fixtures import (
    SIEMENS_DWI_SERIES,
    SIEMENS_DWI_SERIES_PATH,
)
from tests.utils import load_common_sequences
from tests.models import Subject


class SessionModelTestCase(TestCase):
    @classmethod
    @factory.django.mute_signals(signals.post_save)
    def setUpTestData(cls):
        Image.objects.import_path(
            SIEMENS_DWI_SERIES_PATH, progressbar=False, report=False
        )
        cls.series = Series.objects.first()
        cls.subject, _ = Subject.objects.from_dicom_patient(cls.series.patient)
        cls.session = Session.objects.create(
            subject=cls.subject, time=cls.series.datetime
        )
        cls.scan = Scan.objects.create(dicom=cls.series, session=cls.session)

    ##########
    # Fields #
    ##########

    # time
    def test_time_value(self):
        result = self.session.time
        expected = SIEMENS_DWI_SERIES["time"]
        self.assertEqual(result, expected)

    # comments
    def test_comments_value(self):
        result = self.session.comments
        expected = None
        self.assertEqual(result, expected)

    def test_comments_blank_and_null(self):
        field = Session._meta.get_field("comments")
        self.assertTrue(field.blank)
        self.assertTrue(field.null)

    def test_comments_max_length(self):
        field = Session._meta.get_field("comments")
        self.assertEqual(field.max_length, 1000)

    # subject_id
    def test_subject_id_blank_and_null(self):
        field = Session._meta.get_field("subject_id")
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
