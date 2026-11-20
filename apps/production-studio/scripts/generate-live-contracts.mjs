import { readFile, writeFile } from 'node:fs/promises';
const schemas = JSON.parse(await readFile(new URL('../live-contracts.schema.json', import.meta.url), 'utf8'));
const target = new URL('../src/liveGenerated.ts', import.meta.url);
function emit(node, root) {
  if (node.$ref) return emit(root.$defs[node.$ref.split('/').at(-1)], root);
  if ('const' in node) return `z.literal(${JSON.stringify(node.const)})`;
  if (node.enum) return `z.enum(${JSON.stringify(node.enum)})`;
  if (node.oneOf || node.anyOf) return `z.union([${(node.oneOf || node.anyOf).map(n => emit(n, root)).join(',')}])`;
  let expr;
  switch (node.type) {
    case 'object': expr = `z.object({${Object.entries(node.properties).map(([key, value]) => `${JSON.stringify(key)}:${emit(value, root)}${'default' in value ? `.default(${JSON.stringify(value.default)})` : (node.required || []).includes(key) ? '' : '.optional()'}`).join(',')}}).strict()`; break;
    case 'array': expr = `z.array(${emit(node.items, root)})`; break;
    case 'integer': expr = 'z.number().int()'; break;
    case 'number': expr = 'z.number()'; break;
    case 'boolean': expr = 'z.boolean()'; break;
    case 'string': expr = 'z.string()'; break;
    case 'null': return 'z.null()';
    default: throw new TypeError(`Unsupported generated owner schema ${JSON.stringify(node)}`);
  }
  for (const [field, method] of [['minimum','min'],['maximum','max'],['exclusiveMinimum','gt'],['exclusiveMaximum','lt'],['minItems','min'],['maxItems','max'],['minLength','min'],['maxLength','max']]) if (field in node) expr += `.${method}(${node[field]})`;
  if (node.pattern) expr += `.regex(new RegExp(${JSON.stringify(node.pattern)}))`;
  return expr;
}
let output = '// Generated from the Python owner HTTP models. Do not edit.\nimport { z } from "zod";\n';
for (const [name, schema] of Object.entries(schemas)) {
  output += `export const ${name}Schema = ${emit(schema, schema)};\nexport type ${name[0].toUpperCase() + name.slice(1)} = z.infer<typeof ${name}Schema>;\n`;
}
if (process.argv.includes('--check')) {
  if (await readFile(target, 'utf8') !== output) throw new Error('Generated owner contracts drift');
  console.log('Generated owner contracts match exported schema bytes');
} else await writeFile(target, output);
