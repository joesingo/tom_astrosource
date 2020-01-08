from io import StringIO
import logging
import os
from pathlib import Path

import astrosource
import numpy as np
from tom_dataproducts.models import DataProduct, ReducedDatum
from tom_education.models import AsyncError, PipelineProcess, PipelineOutput

from django.conf import settings

class AstrosourceLogBuffer(StringIO):
    """
    Thin wrapper around StringIO that logs messages against a `AstrosourceProcess`
    on write
    """
    def __init__(self, process, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.process = process

    def write(self, s):
        self.process.log(s, end='')
        return super().write(s)


class AstrosourceProcess(PipelineProcess):
    short_name = 'astrosource'
    allowed_suffixes = ['.fz', '.fits.fz', '.psx']
    flags = {
        'calib': {
            'default': False,
            'long_name': 'Perform calibrated photometry to obtain absolute magnitudes'
        },
        'eebls': {
            'default': False,
            'long_name': 'EEBLS - box fitting to search for periodic transits'
        },
        'detrend': {
            'default': False,
            'long_name': 'Detrend exoplanet data'
        },
    }

    class Meta:
        proxy = True

    def copy_input_files(self, tmpdir):
        """
        Copy the input files to the given temporary directory
        """
        for prod in self.input_files.all():
            dest = tmpdir / os.path.basename(prod.data.file.name)  # Use basename of original file
            dest.write_bytes(prod.data.read())

    def do_pipeline(self, tmpdir, **flags):
        """
        Call astrosource to perform the actual analysis
        """
        self.copy_input_files(tmpdir)

        buf = AstrosourceLogBuffer(self)
        logger = logging.getLogger('astrosource')
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.StreamHandler(buf))

        targets = np.array([self.target.ra, self.target.dec, 0, 0])

        # Get file type from the first input file (this assumes that all input
        # files are the same type!)
        filetype = Path(self.input_files.first().data.name).suffix[1:]  # remove the leading '.'

        try:
            with self.update_status('Setting up folders'):
                paths = astrosource.folder_setup(tmpdir)
            with self.update_status('Gathering files'):
                filelist, filtercode = astrosource.gather_files(paths, filetype=filetype)
            with self.update_status('Finding stars'):
                astrosource.find_stars(targets, paths, filelist)
            with self.update_status('Finding comparisons'):
                astrosource.find_comparisons(tmpdir)
            with self.update_status('Calculating curves'):
                astrosource.calculate_curves(targets, parentPath=tmpdir)
            with self.update_status('Performing photometric calculations'):
                astrosource.photometric_calculations(targets, paths=paths)
            if not flags['detrend']:
                with self.update_status('Making plots'):
                    astrosource.make_plots(filterCode=filtercode, paths=paths)
            if flags['detrend']:
                with self.update_status('Detrending'):
                    astrosource.detrend_data(paths, filterCode=filtercode)
            if flags['eebls']:
                with self.update_status('Doing EEBLS'):
                    astrosource.plot_bls(paths=paths)
            if flags['calib']:
                with self.update_status('Making calibrated plots'):
                    astrosource.calibrated_plots(filterCode=filtercode, paths=paths)

        except astrosource.AstrosourceException as ex:
            raise AsyncError(str(ex))

        yield from self.gather_outputs(tmpdir)

    def gather_outputs(self, tmpdir):
        """
        Yield PipelineOutput objects for astrosource output files
        """
        outfiles = [
            # (dirname, filename format string, output type, modes)
            ('outputplots', 'V1_EnsembleVar{}Mag.png', DataProduct, ['Calib', 'Diff']),
            ('outputcats', 'V1_{}Excel.csv', ReducedDatum, ['calib', 'diff']),
        ]

        for dirname, filename, output_type, modes in outfiles:
            outdir = tmpdir / Path(dirname)
            if not outdir.is_dir():
                self.log(f"Output directory '{dirname}' not found")
                continue

            found_file = False
            for mode in modes:
                p = outdir / filename.format(mode)
                if p.is_file():
                    yield PipelineOutput(path=p, output_type=output_type, data_product_type=settings.DATA_PRODUCT_TYPES['photometry'][0])
                    found_file = True
                    break
            if not found_file:
                glob = filename.format('(' + " | ".join(modes) + ')')
                self.log(f"No files matching '{glob}' found in '{dirname}'")
