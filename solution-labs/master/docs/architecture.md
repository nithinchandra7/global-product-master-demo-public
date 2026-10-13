# Implemented architecture and contracts

Regional synthetic records → normalization/quarantine → specification and known-part candidate buckets → deterministic identity evidence / review proposals → cluster constraints → versioned publication.

Identity grain: one manufacturer product, not a group of compatible substitute tires. Manufacturer part numbers and hard specifications establish deterministic matches. Missing part numbers require stewardship; local string similarity is evidence only. Regional season translation is a bounded vocabulary, not an LLM.

Source contract: region + stable source_key, manufacturer, part_number, original description, size, load_index, speed and regional season. Benchmark truth_id lives in a separate evaluation CSV and never enters the matching algorithm.

Decision contract: pair identity, approve/reject, simulated actor, expected workspace revision, decision revision. A rejected pair constrains whole clusters. Source conflicts and unresolved review prevent publication.

Publication contract: products, regional crosswalk, active publish_version and source/decision snapshot digest in one SQLite CAS transaction. Canonical IDs remain stable under non-breaking source corrections. Published identity merges and splits require a migration policy and are rejected locally. Existing canonical fields are identity/member mappings; production attribute survivorship and BOM harmonization are not implemented.

Local resolution trace measures normalization, candidate generation, matching and cluster checks together. It does not invent independent stage timings. Source ingestion connectors, notifications, semantic embedding models and cloud incremental scheduling are reference extensions.
