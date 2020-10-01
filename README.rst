=============================
django-airports-legacy
=============================

Quickstart
----------
Requirements (Ubuntu 16.04)::

    sudo apt-get install -y libsqlite3-mod-spatialite binutils libproj-dev gdal-bin

Install django-airports-legacy::

    pip install django-airports-legacy

Add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'cities',
        'airports',
        'django.contrib.gis',
        ...
    )


Features
--------

The ```airports``` manage command has options, see ```airports --help``` output.
Second run will update the DB with the latest data from the source csv file.

Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox
