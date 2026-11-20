import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const source = new URL('../../../packages/production-contracts/', import.meta.url);
const target = new URL('../src/generated.ts', import.meta.url);
function emit(node, root) {
  if (node.$ref) return emit(root.$defs[node.$ref.split('/').at(-1)], root);
  if ('const' in node) return `z.literal(${JSON.stringify(node.const)})`;
  if (node.enum) return `z.enum(${JSON.stringify(node.enum)})`;
  if (node.oneOf) return `z.union([${node.oneOf.map(n => emit(n, root)).join(',')}])`;
  let expr;
  switch (node.type) {
    case 'object': expr = `z.object({${Object.entries(node.properties).map(([key, value]) => `${JSON.stringify(key)}:${emit(value, root)}${node.required.includes(key) ? '' : '.optional()'}`).join(',')}}).strict()`; break;
    case 'array': expr = `z.array(${emit(node.items, root)})`; break;
    case 'integer': expr = 'z.number().int()'; break;
    case 'boolean': expr = 'z.boolean()'; break;
    case 'string': expr = 'z.string()'; break;
    default: throw new TypeError(`Unsupported generated schema node ${JSON.stringify(node)}`);
  }
  for (const [field, method] of [['minimum','min'],['maximum','max'],['minItems','min'],['maxItems','max']]) if (field in node) expr += `.${method}(${node[field]})`;
  if (node.pattern) expr += `.regex(new RegExp(${JSON.stringify(node.pattern)}))`;
  return expr;
}
let output = '// Generated from packages/production-contracts; npm run contracts. Do not edit.\nimport { z } from "zod";\n';
for (const [file, name] of [['effects','effect'],['reaction','reactionPack'],['applied-ack','appliedAck'],['capability','capability']]) {
  const schema = JSON.parse(await readFile(new URL(`${file}.schema.json`, source), 'utf8'));
  output += `export const ${name}Schema = ${emit(schema, schema)};\nexport type ${name[0].toUpperCase() + name.slice(1)} = z.infer<typeof ${name}Schema>;\n`;
}
if (process.argv.includes('--check')) {
  if (await readFile(target, 'utf8') !== output) throw new Error('Generated contracts drift; run npm run contracts');
  console.log('Generated contracts match canonical schema bytes');
} else { await writeFile(target, output); console.log(fileURLToPath(target)); }
