# tom_astrosource

This package allows [astrosource](https://github.com/zemogle/astrosource/) to
be run on data files in the [TOM Toolkit](https://tomtoolkit.github.io/) via
the [tom_education](https://github.com/joesingo/tom_education) app.

## Requirements

In addition to the requirements listed in `setup.py` you will need:

- A working TOM (see [TOM Toolkit](https://tomtoolkit.github.io/) documentation)
- Python > 3.6

## Installation

1. Set up a TOM and the `tom_education` package. See the [tom_education
  installation
  instructions](https://github.com/joesingo/tom_education#installation).

```
pip install tom_astrosource
```

3. Add `tom_astrosource` to `INSTALLED_APPS` in `settings.py`.

```python
INSTALLED_APPS = [
    ...
    'tom_astrosource'
]
```

4. Add the `astrosource` pipeline to `TOM_EDUCATION_PIPELINES` (create this
setting if it does not exist):

```python
TOM_EDUCATION_PIPELINES = {
    ...
    'astrosource': 'tom_astrosource.models.AstrosourceProcess'
}
```

### Install Development version

Clone this repo and install the package with `pip`:

```
git clone https://github.com/joesingo/tom_astrosource
pip install tom_astrosource
```

## Usage

See the [pipeline
documentation](https://github.com/joesingo/tom_education/blob/master/doc/pipelines.md)
in `tom_education` for how to run the pipeline on your data.
