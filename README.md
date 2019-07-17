# tom_autovar

This package allows [autovar](https://github.com/zemogle/autovar/) to be run on
data files in the [TOM Toolkit](https://tomtoolkit.github.io/) via the
[tom_education](https://github.com/joesingo/tom_education) app.

## Installation

1. Set up a TOM and the `tom_education` package. See the [tom_education
  installation
  instructions](https://github.com/joesingo/tom_education#installation).

2. Clone this repo and install the package with `pip`:

```
git clone <this repo>
pip install tom_autovar
```

3. Add `tom_autovar` to `INSTALLED_APPS` in `settings.py`.

```python
INSTALLED_APPS = [
    ...
    'tom_autovar'
]
```

4. Add the `autovar` pipeline to `TOM_EDUCATION_PIPELINES` (create this setting
if it does not exist):

```python
TOM_EDUCATION_PIPELINES = {
    ...
    'autovar': 'tom_autovar.models.AutovarProcess'
}
```

## Usage

See the [pipeline
documentation](https://github.com/joesingo/tom_education/blob/master/doc/pipelines.md)
in `tom_education` for how to run the pipeline on your data.
