# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-06-02

### Fixed

- `X | Y` union annotations in payloads now produce an `anyOf` schema on
  Python 3.11 through 3.13. The union check previously looked for
  `UnionType` on the `typing` module, where it does not exist on those
  versions, so unions silently fell back to an empty schema. It now reads
  `UnionType` from the `types` module.

## [0.1.0] - 2026-06-02

Initial release.

### Added

- `@document_action` and `@document_event` decorators for annotating
  Channels consumer methods with summaries, descriptions, payloads,
  tags, and examples.
- `AsyncAPIGenerator` that builds a valid [AsyncAPI 3.0](https://www.asyncapi.com)
  specification from one or more annotated consumers, preserving method
  definition order.
- Payload schema extraction from `@dataclass`, [Pydantic](https://docs.pydantic.dev)
  models, and Django REST Framework serializers.
- `AsyncAPISpecView` serving the spec as `application/yaml`, and
  `AsyncAPIDocView` rendering a hosted viewer UI with syntax-highlighted
  message schemas.
- Multi-consumer specs with namespaced message and operation IDs, plus a
  spec-switcher dropdown in the viewer for browsing several consumers.
- Interactive try-it-out WebSocket console with an auth-method selector
  for session cookie, cookie JWT, and query-param JWT.
- Security scheme generation from `AUTH_QUERY_PARAM` (`queryToken`) and
  `AUTH_COOKIE_NAME` (`cookieJWT`) settings.
- `export_asyncapi` management command with a generator mode (from
  annotated consumers) and a template mode (from hand-written YAML).
- Configuration via the `CHANNELS_SPECTACULAR_SETTINGS` dict, with
  request-derived or statically pinned `servers` blocks.
