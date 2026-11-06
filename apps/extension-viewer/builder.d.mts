import type { ParsedPack } from '../../packages/extension-preview/index.mjs';
export interface Draft { packId: string; packVersion: string; durationMs: string; cues: { atMs: string; value: string }[] }
export interface CompiledDraft { bytes: Uint8Array<ArrayBuffer>; pack: ParsedPack }
export function newDraft(preset?: string): Draft;
export function draftFromPack(pack: ParsedPack): Draft;
export function compileDraft(draft: Draft): CompiledDraft;
