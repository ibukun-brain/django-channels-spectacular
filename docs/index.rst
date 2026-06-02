django-channels-spectacular
===========================

.. rubric:: Auto-generate interactive AsyncAPI 3.0 docs for your Django Channels WebSocket consumers.

.. image:: https://github.com/ibukun-brain/django-channels-spectacular/actions/workflows/ci.yml/badge.svg?branch=master
   :target: https://github.com/ibukun-brain/django-channels-spectacular/actions/workflows/ci.yml
   :alt: Tests

.. image:: https://readthedocs.org/projects/django-channels-spectacular/badge/?version=latest
   :target: https://django-channels-spectacular.readthedocs.io/en/latest/
   :alt: Documentation status

.. image:: https://codecov.io/gh/ibukun-brain/django-channels-spectacular/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/ibukun-brain/django-channels-spectacular
   :alt: Coverage

**django-channels-spectacular** is the missing documentation layer for
`Django Channels <https://channels.readthedocs.io>`_ — think of it as
`drf-spectacular <https://drf-spectacular.readthedocs.io>`_ for WebSockets.
Annotate your consumer's action handlers once and get a live, browsable
`AsyncAPI 3.0 <https://www.asyncapi.com>`_ spec served straight from your
Django app. No separate tooling, no manual YAML, no drift between code and docs.

**What you get out of the box:**

- A ``View`` serving ``asyncapi.yaml`` with a fully valid `AsyncAPI 3.0 <https://www.asyncapi.com/docs/reference/specification/v3.0.0>`_ spec
- A hosted viewer UI with syntax-highlighted message schemas
- An interactive try-it-out WebSocket console for testing from the browser
- Support for ``@dataclass``, `Pydantic <https://docs.pydantic.dev>`_ models, and DRF serializers as message payloads
- Multi-consumer docs with a spec-switcher dropdown
- Query-param jwt, cookie jwt and session-cookie authentication schemes

.. tip::
   Prefer to see it running? A complete chat + notifications project lives in
   the `example/ <https://github.com/ibukun-brain/django-channels-spectacular/tree/main/example>`_
   directory — see :doc:`example-app`.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   installation
   quickstart
   example-app
   configuration

.. toctree::
   :maxdepth: 2
   :caption: Guides

   authentication
   multi-consumer
   export-command
   payload-types
   hand-written-yaml
   try-it-out

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api-reference
   settings-reference

.. toctree::
   :maxdepth: 1
   :caption: Project

   changelog
   contributing
   license


License
-------

Provided by `Ibukun Olaifa <https://github.com/ibukun-brain>`_.
Licensed under the `3-Clause BSD License <https://github.com/ibukun-brain/django-channels-spectacular/blob/main/LICENSE>`_.


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
