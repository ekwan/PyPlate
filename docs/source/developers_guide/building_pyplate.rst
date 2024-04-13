.. _building_pyplate:

Building Pyplate
================

.. note:: When a new version of PyPlate is ready to be released, the version number in `pyproject.toml` should be updated. ``version = "0.4.1"``

In order to build and upload PyPlate to the PyPi repository, you will need to install the `build` and `twine` packages. You can install these packages by running the following command:

.. code-block:: bash

    pip install build twine

You can build PyPlate for uploading to the PyPi repository by running the following command in the root directory of the project:

.. code-block:: bash

    python -m build

This will build a sdist and wheel file in the `dist` directory.

- sdist file: This is a source distribution file that can be built and installed on a user's machine. It ends in `.tar.gz`.
- wheel file: This is a binary distribution file that can be directly installed.

You can upload the built files to the PyPi repository by running the following command:

.. code-block:: bash

    twine upload dist/*


PyPi Authentication
"""""""""""""""""""

PyPi only allows authentication via an API token. You can create an API token by following the instructions on the `PyPi website <https://pypi.org/manage/account/token/>`_
|br| twine will ask for a username and passed. The username will be "__token__" and the password will be the API token you created.

The API token can be stored for automated authentication in the `~/.pypirc` file. The file should look like this:

.. code-block:: ini

    [pypi]
      username = __token__
      password = <your API token>

In lieu of storing your API token in plaintext, you can use the `keyring` package to store your API token in your system's keyring::

    keyring set https://upload.pypi.org/legacy/ __token__
    keyring set https://test.pypi.org/legacy/ __token__

- If `keyring` is not installed, you can install it by running `pip install keyring`


Test PyPi
"""""""""

If you have an account on https://test.pypi.org/, you can upload the package to the test repository by running the following command:

.. code-block:: bash

    twine upload --repository testpypi dist/*

This is useful for testing the package before uploading it to the main PyPi repository.

You can install the package from the test repository by running the following command:

.. code-block:: bash

    pip install --index-url https://test.pypi.org/simple/ pyplate-hte
