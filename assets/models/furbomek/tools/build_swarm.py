"""Nine source miniatures. Run in Blender with -- --output DIRECTORY."""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--references', type=Path)
    parser.add_argument('--ids', default='1,2,3,4,5,6,7,8,9')
    parser.add_argument('--no-render', action='store_true', help='Compatibility flag; this source builder does not render previews')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    ids = [int(item) for item in args.ids.split(',')]
    if not ids or len(set(ids)) != len(ids) or any(n not in range(1, 10) for n in ids):
        parser.error('--ids must contain distinct numbers from 1 through 9')
    root = Path(__file__).resolve().parent
    output = args.output.resolve()
    pack = root.parent
    if output == pack or pack in output.parents:
        parser.error('--output must be outside the committed asset pack')
    import bpy
    from mathutils import Vector
    sys.path.insert(0, str(root))
    import models_a
    import models_b
    brief = json.loads((root / 'design_brief.json').read_text())
    output.mkdir(parents=True, exist_ok=True)
    for n in ids:
        spec = brief['models'][n - 1]
        stem = f"{n:02d}_{spec['slug']}"
        targets = [output / (stem + ext) for ext in ('.blend', '.glb')]
        if any(path.exists() for path in targets):
            parser.error(f'refusing to overwrite existing outputs for {stem}')
    for n in ids:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        spec = brief['models'][n - 1]
        builder = getattr(models_a if n in (1, 2, 3, 4, 9) else models_b, f'build_{n:02d}')()
        bpy.context.view_layer.update()
        objects = list(builder.collection.objects)
        low_z = min((o.matrix_world @ Vector(c)).z for o in objects if o.type == 'MESH' for c in o.bound_box)
        builder.root.location.z -= low_z
        bpy.context.view_layer.update()
        builder.root['features'] = json.dumps(spec['features'])
        bpy.context.scene['source_note'] = 'Reference/inferred artistic proportions; not measured or verified hardware.'
        if args.references:
            reference = args.references / spec['reference']
            if reference.is_file():
                image = bpy.data.images.load(str(reference.resolve()), check_existing=True)
                image.pack()
                image.filepath = '//references/' + reference.name
        stem = f"{n:02d}_{spec['slug']}"
        bpy.ops.wm.save_as_mainfile(filepath=str(output / (stem + '.blend')))
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = builder.root
        bpy.ops.export_scene.gltf(filepath=str(output / (stem + '.glb')), export_format='GLB', use_selection=True, export_apply=True)
    print(f'Built {len(ids)} source miniatures in {output}; exports are full detail, not game-chunked.')


if __name__ == '__main__':
    main()
