"""Read-only asset inventory, hash, container and game triangle checks (stdlib)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative_file(root, value):
    path = Path(value)
    require(not path.is_absolute() and '..' not in path.parts, f'unsafe manifest path: {value}')
    resolved = (root / path).resolve()
    require(root in resolved.parents and resolved.is_file(), f'missing/outside pack: {value}')
    return resolved


def glb_geometry(path):
    data = path.read_bytes()
    require(len(data) >= 20, f'truncated GLB: {path.name}')
    magic, version, length = struct.unpack_from('<4sII', data)
    require(magic == b'glTF' and version == 2 and length == len(data), f'invalid GLB header: {path.name}')
    cursor, document = 12, None
    while cursor < length:
        require(cursor + 8 <= length, f'truncated chunk: {path.name}')
        size, kind = struct.unpack_from('<I4s', data, cursor)
        cursor += 8
        require(size % 4 == 0 and cursor + size <= length, f'invalid chunk: {path.name}')
        if kind == b'JSON':
            document = json.loads(data[cursor:cursor + size])
        cursor += size
    require(document is not None, f'GLB JSON missing: {path.name}')
    counts = []
    for mesh in document.get('meshes', []):
        count = 0
        for primitive in mesh['primitives']:
            require(primitive.get('mode', 4) == 4, f'non-triangle GLB primitive: {path.name}')
            accessor = primitive.get('indices', primitive.get('attributes', {}).get('POSITION'))
            require(accessor is not None, f'missing accessor: {path.name}')
            vertices = document['accessors'][accessor]['count']
            require(vertices % 3 == 0, f'incomplete triangle: {path.name}')
            count += vertices // 3
        require(0 < count <= 18000, f'game mesh exceeds 18,000 triangles: {path.name}: {count}')
        counts.append(count)
    require(counts and document.get('nodes'), f'empty GLB: {path.name}')
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = json.loads((root / 'manifest.json').read_text())
    assets = manifest['assets']
    require(len(assets) == 10 and len({a['id'] for a in assets}) == 10, 'expected ten unique assets')
    entries = manifest['files']
    require(len({entry['path'] for entry in entries}) == len(entries), 'duplicate manifest paths')
    indexed = {entry['path'] for entry in entries}
    for entry in entries:
        path = relative_file(root, entry['path'])
        require(path.stat().st_size == entry['size_bytes'], f'size mismatch: {entry["path"]}')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else hashlib.sha256(stream.read()).hexdigest()
        require(digest == entry['sha256'], f'SHA256 mismatch: {entry["path"]}')
        if path.suffix.lower() == '.fbx':
            with path.open('rb') as stream:
                require(stream.read(23) == b'Kaydara FBX Binary  \x00\x1a\x00', f'not binary FBX: {path.name}')
    chunks, triangles = 0, 0
    for asset in assets:
        for kind in ('blender', 'glb', 'fbx'):
            value = asset['files'][kind]
            require(value in indexed, f'unhashed asset file: {value}')
            relative_file(root, value)
        counts = glb_geometry(relative_file(root, asset['files']['glb']))
        geometry = asset['geometry']
        require(len(counts) == geometry['game_mesh_chunks'], f'chunk mismatch: {asset["id"]}')
        require(sum(counts) == geometry['glb_triangles'], f'triangle mismatch: {asset["id"]}')
        chunks += len(counts)
        triangles += sum(counts)
    # Public text/metadata only. Binary internals require Blender/Studio inspection.
    private = re.compile(r'(?:/(?:Users|home)/[^/\s]+|[A-Za-z]:\\Users\\|sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)')
    for path in root.rglob('*'):
        if path.suffix.lower() in ('.md', '.json', '.py', '.lua', '.txt') and '__pycache__' not in path.parts:
            require(not private.search(path.read_text()), f'possible private path/secret in {path.relative_to(root)}')
    print(f'PASS: {len(entries)} hashed files, 10 assets, {chunks} GLB chunks, {triangles} triangles; metadata scan clean')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, struct.error) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
