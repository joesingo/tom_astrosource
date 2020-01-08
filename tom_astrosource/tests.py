from datetime import datetime
from django.core.files.uploadedfile import File
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import tempfile

from django.test import TestCase
from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm
from tom_education.models import PipelineOutput
from tom_dataproducts.models import DataProduct, ReducedDatum
from tom_targets.models import Target

from tom_astrosource.models import AstrosourceProcess, AstrosourceLogBuffer


class AstrosourceProcessTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        target_identifier = 't{}'.format(datetime.now().timestamp())
        cls.target = Target.objects.create(name=target_identifier)
        cls.prods = [DataProduct.objects.create(product_id=f'test_{i}', target=cls.target)
                     for i in range(4)]
        for prod in cls.prods:
            fn = f'{prod.product_id}_file'
            prod.data.save(fn, File(BytesIO()))

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='test', email='test@example.com')
        self.client.force_login(self.user)
        assign_perm('tom_targets.view_target', self.user, self.target)

    def test_copy_input_files(self):
        proc = AstrosourceProcess.objects.create(identifier='someprocess', target=self.target)
        proc.input_files.add(*self.prods)
        proc.save()

        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir = Path(tmpdir_name)
            proc.copy_input_files(tmpdir)
            listing = {p.name for p in tmpdir.iterdir()}
        self.assertEqual(listing, {
            'test_0_file', 'test_1_file', 'test_2_file', 'test_3_file'
        })

    def test_gather_outputs(self):
        proc = AstrosourceProcess.objects.create(identifier='someprocess', target=self.target)
        proc.input_files.add(*self.prods)
        proc.save()

        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir = Path(tmpdir_name)
            plots = tmpdir / 'outputplots'
            plots.mkdir()
            cats = tmpdir / 'outputcats'
            cats.mkdir()

            # Make both diff and calib files; calib should be preferred
            calib_png = plots / 'V1_EnsembleVarCalibMag.png'
            calib_png.write_bytes(b'calib data')
            (plots / 'V1_EnsembleVarDiffMag.png').write_bytes(b'diff data')

            # Make only diff file
            diff_csv = cats / 'V1_diffExcel.csv'
            diff_csv.write_text('comma separated')

            # Extra files should be ignored without causing errors
            (plots / 'suspicious_file.sh').write_text('sudo rm -rf /')

            outputs = set(proc.gather_outputs(tmpdir))

        self.assertEqual(outputs, {
            PipelineOutput(path=calib_png, output_type=DataProduct, data_product_type='photometry'),
            PipelineOutput(path=diff_csv, output_type=ReducedDatum, data_product_type='photometry')
        })
        self.assertIsNone(proc.logs)

    def test_missing_outputs(self):
        proc = AstrosourceProcess.objects.create(identifier='someprocess', target=self.target)
        proc.input_files.add(*self.prods)
        proc.save()

        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir = Path(tmpdir_name)
            (tmpdir / 'outputplots').mkdir()
            outputs = set(proc.gather_outputs(tmpdir))

        self.assertEqual(outputs, set([]))
        self.assertTrue(proc.logs)
        log_lines = proc.logs.strip().split("\n")
        self.assertEqual(log_lines, [
            "No files matching 'V1_EnsembleVar(Calib | Diff)Mag.png' found in 'outputplots'",
            "Output directory 'outputcats' not found"
        ])

    def test_log_buffer(self):
        proc = AstrosourceProcess.objects.create(identifier='someprocess', target=self.target)
        proc.input_files.add(*self.prods)
        proc.save()

        buf = AstrosourceLogBuffer(proc)
        buf.write('hello there')
        self.assertEqual(proc.logs, 'hello there')
        buf.write('. how are you?')
        self.assertEqual(proc.logs, 'hello there. how are you?')
