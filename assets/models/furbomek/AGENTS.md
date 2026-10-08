# Character asset guidance

Read the root AGENTS.md, this directory's README, manifest.json, and provenance.json before changes. Preserve all ten distinct designs and the full-detail Blender sources. Game exports are reduced, static, unrigged derivatives; never replace a source with its optimized export.

Geometry proportions are reference/inferred, not measured hardware. Do not invent a license grant, source clearance, or Phase 5 runtime capability. Licensing and public redistribution remain an owner decision. Raw private references are intentionally omitted.

Use Blender 5.2.2 for the observed pipeline. Rebuild into a separate output directory; do not overwrite tracked assets during experiments. The nine-mini generator is an editable starting point, not a bit-identical reproduction of later edits. F-069 is edited from its supplied Blender file.

After authorized asset changes, update manifest hashes, byte sizes, geometry counts and provenance, then run `python3 tools/validate_assets.py`. Keep Blender/GLB/FBX/RBXL files under the root's scoped LFS rules. Exclude backups, caches, credentials, private references, logs, and machine-specific paths. Validate Blender internals separately: text scanning cannot prove binary privacy.

Roblox MeshIds are account-owned. Rebinding must operate only on the named imported bundle and archive existing characters in ServerStorage. Never destroy the environment, camera, or motion scripts. Do not run scene mutations merely to validate source syntax.
