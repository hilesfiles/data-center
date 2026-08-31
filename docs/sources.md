# Source registry

The initial machine-readable source registry is `config/v1/source-registry.json`.
It is seeded from the project specifications and intentionally marked as not yet network
verified.

Each acquisition adapter must create an acquisition manifest and source artifact record
containing the request URL, retrieval time, response status, content hash, storage policy,
license, and parser version. A mutable URL without retrieval metadata is insufficient.

Discovery sources such as news archives and search indexes identify candidates. They do
not automatically establish canonical facts. Attribute-specific evidence quality and
independence are considered during claim resolution.

