.. _building_documentation:

Building Documentation
======================

The documentation is built using `Sphinx <http://sphinx-doc.org/>`_.

In order to build the documentation, some dependencies are required. You can install them using the following command:

.. code-block:: bash

    pip install -r docs/requirements.txt

Then, you can build the documentation using the following command:

.. code-block:: bash

    make -C docs html

It is also possible to automatically rebuild the documentation when a file is modified using the following command:

.. code-block:: bash

    sphinx-autobuild docs/source docs/_build/html

This is helpful when you are working on the documentation and want to see the changes in real-time.
