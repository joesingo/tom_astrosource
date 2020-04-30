from io import StringIO
import logging
import os
from pathlib import Path

from astrosource import TimeSeries
from astrosource.detrend import detrend_data
from astrosource.eebls import plot_bls
from astrosource.utils import AstrosourceException
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
        'plot': {
            'default': False,
            'long_name': 'Create plot files'
        },
        'period': {
            'default': False,
            'long_name': 'Perform automatic period finding'
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
        return [prod.data.file for prod in self.input_files.all()]
        # for prod in self.input_files.all():
        #     dest = tmpdir / os.path.basename(prod.data.file.name)  # Use basename of original file
        #     dest.write_bytes(prod.data.read())

    def do_pipeline(self, tmpdir, **flags):
        """
        Call astrosource to perform the actual analysis
        """
        with self.update_status('Gathering data files'):
            filelist = self.copy_input_files(tmpdir)

        buf = AstrosourceLogBuffer(self)
        logger = logging.getLogger('astrosource')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler(buf))

        targets = np.array([self.target.ra, self.target.dec, 0, 0])

        # Get file type from the first input file (this assumes that all input
        # files are the same type!)
        filetype = Path(self.input_files.first().data.name).suffix[1:]  # remove the leading '.'

        try:
            with self.update_status('Initialising'):
                ts = TimeSeries(indir=tmpdir, filelist=filelist, targets=targets, verbose=True)
            with self.update_status('Analysing input data files'):
                ts.analyse(calib=True)
            with self.update_status('Calculating curves'):
                ts.find_stable()
            with self.update_status('Performing photometric calculations'):
                ts.photometry()
            if flags['plot']:
                with self.update_status('Plotting results and finding period'):
                    ts.plot(period=flags['period'], filesave=True)
            if flags['detrend']:
                with self.update_status('Detrending'):
                    detrend_data(ts.paths, filterCode=ts.filtercode)
            if flags['eebls']:
                with self.update_status('Doing EEBLS'):
                    plot_bls(paths=ts.paths)

        except AstrosourceException as ex:
            raise AsyncError(str(ex))

        yield from self.gather_outputs(ts, tmpdir)

    def gather_outputs(self, timeseries, tmpdir):
        """
        Yield PipelineOutput objects for astrosource output files
        """
        timeseries.usedimages.sort()
        filesused = [timeseries.files[i] for i in timeseries.usedimages]
        photdata = [x for x in zip(timeseries.data[0][:,6],timeseries.data[0][:,10],timeseries.data[0][:,11],filesused)]

        outputs = []
        for pd in photdata:
            yield PipelineOutput(path=None, data=pd, output_type=ReducedDatum, data_product_type=settings.DATA_PRODUCT_TYPES['photometry'][0])

        # These data products are PLOTS
        outfiles = [
            # (dirname, filename format string, output type, modes)
            ('outputplots', 'V1_EnsembleVar{}Mag.png', DataProduct, ['Calib', 'Diff']),
            ('periods', 'V1_StringTestPeriodPlot{}.png', DataProduct, ['_calibrated', '']),
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
                    yield PipelineOutput(path=p, output_type=output_type, data_product_type=settings.DATA_PRODUCT_TYPES['plot'][0], data=None)
                    found_file = True
                    break
            if not found_file:
                glob = filename.format('(' + " | ".join(modes) + ')')
                self.log(f"No files matching '{glob}' found in '{dirname}'")
