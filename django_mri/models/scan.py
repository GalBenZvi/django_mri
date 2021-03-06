import warnings

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel
from django_mri.interfaces.dcm2niix import Dcm2niix
from django_mri.models import messages
from django_mri.models.managers.scan import ScanManager
from django_mri.models.nifti import NIfTI
from django_mri.models.sequence_type import SequenceType
from django_mri.utils.utils import get_subject_model, get_group_model
from django_mri.utils.bids import Bids
from pathlib import Path


class Scan(TimeStampedModel):
    """
    A model used to represent an MRI scan independently from the file-format in
    which it is saved. This model handles any conversions between formats in case
    they are required, and allows for easy querying of MRI scans based on universal
    attributes.

    """

    institution_name = models.CharField(max_length=64, blank=True, null=True)
    time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="The time in which the scan was acquired.",
    )
    description = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="A short description of the scan's acqusition parameters.",
    )
    number = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="The number of this scan relative to the session in which it was acquired.",
    )

    # Relatively universal MRI scan attributes. These might be infered from the
    # raw file's meta-data.
    echo_time = models.FloatField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="The time between the application of the radiofrequency excitation pulse and the peak of the signal induced in the coil (in milliseconds).",
    )
    repetition_time = models.FloatField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="The time between two successive RF pulses (in milliseconds).",
    )
    inversion_time = models.FloatField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="The time between the 180-degree inversion pulse and the following spin-echo (SE) sequence (in milliseconds).",
    )
    spatial_resolution = ArrayField(
        models.FloatField(), size=3, blank=True, null=True
    )

    comments = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="If anything noteworthy happened during acquisition, it may be noted here.",
    )

    # If this instance's origin is a DICOM file, or it was saved as one, this field
    # keeps the relation to that django_dicom.Series instance.
    dicom = models.OneToOneField(
        "django_dicom.Series",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="scan",
        verbose_name="DICOM Series",
    )
    # Keep track of whether we've updated the instance's fields from the DICOM
    # header data.
    is_updated_from_dicom = models.BooleanField(default=False)

    # If converted to NIfTI, keep a reference to the resulting instance.
    # The reason it is suffixed with an underline is to allow for "nifti"
    # to be used as a property that automatically returns an existing instance
    # or creates one.
    _nifti = models.OneToOneField(
        "django_mri.NIfTI", on_delete=models.SET_NULL, blank=True, null=True
    )

    subject = models.ForeignKey(
        get_subject_model(),
        on_delete=models.PROTECT,
        related_name="mri_scans",
        blank=True,
        null=True,
    )

    study_groups = models.ManyToManyField(
        get_group_model(), related_name="mri_scans", blank=True
    )

    added_by = models.ForeignKey(
        get_user_model(),
        related_name="mri_uploads",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    objects = ScanManager()

    class Meta:
        verbose_name_plural = "MRI Scans"

    def __str__(self) -> str:
        return self.description

    def save(self, *args, **kwargs) -> None:
        if self.dicom and not self.is_updated_from_dicom:
            self.update_fields_from_dicom()
        super().save(*args, **kwargs)

    def update_fields_from_dicom(self) -> None:
        """
        Sets instance fields from related DICOM series.
        TODO: Needs refactoring.

        Raises
        ------
        AttributeError
            If not DICOM series is related to this scan.
        """

        if self.dicom:
            self.institution_name = self.dicom.institution_name
            self.number = self.dicom.number
            self.time = self.dicom.datetime
            self.description = self.dicom.description
            self.echo_time = self.dicom.echo_time
            self.inversion_time = self.dicom.inversion_time
            self.repetition_time = self.dicom.repetition_time
            self.spatial_resolution = self.dicom.spatial_resolution
            self.is_updated_from_dicom = True
        else:
            raise AttributeError(
                f"No DICOM data associated with MRI scan {self.id}!"
            )

    def infer_sequence_type_from_dicom(self) -> SequenceType:
        """
        Returns the appropriate :class:`django_mri.SequenceType` instance according to
        the scan's "*ScanningSequence*" and "*SequenceVariant*" header values.


        Returns
        -------
        SequenceType
            A SequenceType instance.
        """

        try:
            return SequenceType.objects.get(
                scanning_sequence=self.dicom.scanning_sequence,
                sequence_variant=self.dicom.sequence_variant,
            )
        except models.ObjectDoesNotExist:
            return None

    def infer_sequence_type(self) -> SequenceType:
        if self.dicom:
            return self.infer_sequence_type_from_dicom()

    def get_default_nifti_dir(self) -> Path:
        """
        Returns the default location for the creation of a NIfTI version of the
        scan. Currently only conversion from DICOM is supported.

        Returns
        -------
        str
            Default location for conversion output.
        """

        if self.dicom:
            path = str(self.dicom.path).replace("DICOM", "NIfTI")
            return Path(path)

    def get_default_nifti_name(self) -> str:
        """
        Returns the default file name for a NIfTI version of this scan.

        Returns
        -------
        str
            Default file name.
        """

        return str(self.id)

    def get_default_nifti_destination(self) -> Path:
        """
        Returns the default path for a NIfTI version of this scan.

        Returns
        -------
        str
            Default path for NIfTI file.
        """

        directory = self.get_default_nifti_dir()
        name = self.get_default_nifti_name()
        return directory / name

    def get_bids_destination(self):
        bids_path = Bids(self).compose_bids_path()
        return bids_path

    def compile_to_bids(self, bids_path: Path):
        Bids(self).clean_unwanted_files(bids_path)
        Bids(self).fix_functional_json(bids_path)

    def dicom_to_nifti(
        self,
        destination: Path = None,
        compressed: bool = True,
        generate_json: bool = True,
    ) -> NIfTI:
        """
        Convert this scan from DICOM to NIfTI using _dcm2niix.

        .. _dcm2niix: https://github.com/rordenlab/dcm2niix

        Parameters
        ----------
        destination : Path, optional
            The desired path for conversion output (the default is None, which
            will create the file in some default location).

        Raises
        ------
        AttributeError
            If no DICOM series is related to this scan.

        Returns
        -------
        NIfTI
            A :class:`django_mri.NIfTI` instance referencing the conversion output.
        """

        if self.sequence_type and self.sequence_type.title == "Localizer":
            warnings.warn("Localizer scans may not converted to NIfTI.")
            return None
        if self.dicom:
            dcm2niix = Dcm2niix()
            if destination is None:
                try:
                    destination = self.get_bids_destination()
                except ValueError as e:
                    print(e.args)
                    destination = self.get_default_nifti_destination()
            elif not isinstance(destination, Path):
                destination = Path(destination)
            destination.parent.mkdir(exist_ok=True, parents=True)
            nifti_path = dcm2niix.convert(
                self.dicom.get_path(),
                destination,
                compressed=compressed,
                generate_json=generate_json,
            )
            self.compile_to_bids(destination)
            nifti = NIfTI.objects.create(path=nifti_path, is_raw=True)
            return nifti
        else:
            message = messages.DICOM_TO_NIFTI_NO_DICOM.format(scan_id=self.id)
            raise AttributeError(message)

    # def recon_all(self, **configuration):
    #     if self.is_mprage or self.is_spgr:
    #         recon_all = get_lastest_analysis_version("ReconAll")
    #         recon_all_node, _ = Node.objects.get_or_create(
    #             analysis_version=recon_all, configuration=configuration
    #         )
    #         nifti_path = str(self.nifti.uncompressed)
    #         results = recon_all_node.run(inputs={"T1_files": [nifti_path]})
    #         self.nifti.compress()
    #         return results
    #     else:
    #         raise TypeError(
    #             "Only MPRAGE or SPGR scans may be given as input to ReconAll!"
    #         )

    def warn_subject_mismatch(self, subject):
        message = messages.SUBJECT_MISMATCH.format(
            scan_id=self.id,
            existing_subject_id=self.subject.id,
            assigned_subject_id=subject.id,
        )
        warnings.warn(message)

    def suggest_subject(self, subject) -> None:
        if subject is not None:
            # If this scan actually belongs to a different subject (and self.subject
            # is not None), warn the user and return.
            mismatch = self.subject != subject
            if self.subject and mismatch:
                self.warn_subject_mismatch(subject)
            # Else, if this scan is not assigned to any subject but a subject was
            # provided (and not None), associate this scan with it.
            else:
                self.subject = subject
                self.save()

    @property
    def sequence_type(self) -> SequenceType:
        return self.infer_sequence_type()

    @property
    def nifti(self) -> NIfTI:
        if not isinstance(self._nifti, NIfTI):
            self._nifti = self.dicom_to_nifti()
            self.save()
        return self._nifti
