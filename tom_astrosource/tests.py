from datetime import datetime
from django.core.files.uploadedfile import File
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import tempfile

from django.test import TestCase
from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm
from tom_dataproducts.models import DataProduct
from tom_targets.models import Target

from tom_astrosource.models import AstrosourceProcess, AstrosourceLogBuffer


class AstrosourceProcessTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        target_identifier = 't{}'.format(datetime.now().timestamp())
        cls.target = Target.objects.create(identifier=target_identifier, name='my target')
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

    @patch('tom_astrosource.models.AstrosourceProcess.output_dirs', ['one', 'two', 'nonexistant'])
    def test_gather_outputs(self):
        proc = AstrosourceProcess.objects.create(identifier='someprocess', target=self.target)
        proc.input_files.add(*self.prods)
        proc.save()

        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir = Path(tmpdir_name)
            one = tmpdir / 'one'
            one_subdir = one / 'subdir'
            two = tmpdir / 'two'
            three = tmpdir / 'three'
            one.mkdir()
            one_subdir.mkdir()
            two.mkdir()
            three.mkdir()

            file1 = one / 'file1.png'
            file2 = one / 'file2.bmp'
            file3 = two / 'file3.tar.gz'
            file4 = three / 'file4.txt'

            file1.write_text('hello')
            file2.write_text('hello')
            file3.write_text('hello')
            file4.write_text('hello')

            outputs = set(proc.gather_outputs(tmpdir))
        self.assertEqual(outputs, {file1, file2, file3})

    def test_log_buffer(self):
        proc = AstrosourceProcess.objects.create(identifier='someprocess', target=self.target)
        proc.input_files.add(*self.prods)
        proc.save()

        buf = AstrosourceLogBuffer(proc)
        buf.write('hello there')
        self.assertEqual(proc.logs, 'hello there')
        buf.write('. how are you?')
        self.assertEqual(proc.logs, 'hello there. how are you?')
