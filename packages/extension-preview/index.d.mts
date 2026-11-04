/** Exact public data contract of index.mjs; only parsePack creates branded packs. */
declare const parsedPackBrand: unique symbol;
export type Expression = 'neutral' | 'curious';
export type Reaction = 'acknowledge';
export type PreviewEvent = Readonly<{ seq: number; atMs: number } & (
  { kind: 'presentation.expression'; value: Expression } |
  { kind: 'presentation.reaction'; value: Reaction }
)>;
export interface ParsedPack {
  readonly [parsedPackBrand]: true;
  readonly schemaVersion: 1;
  readonly packId: string;
  readonly packVersion: string;
  readonly previewContractVersion: 1;
  readonly capabilities: readonly ('presentation.expression' | 'presentation.reaction')[];
  readonly durationMs: number;
  readonly events: readonly PreviewEvent[];
}
export interface Sample {
  readonly positionMs: number;
  readonly expression: Expression;
  readonly reaction: Reaction | null;
  readonly reactionProgress: number;
}
export const MAX_PACK_BYTES: number;
export function parsePack(bytes: Uint8Array): ParsedPack;
export function samplePack(pack: ParsedPack, positionMs: number): Sample;
