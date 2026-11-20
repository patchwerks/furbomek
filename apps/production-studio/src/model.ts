import { z } from 'zod';
import type { Effect } from './generated.ts';
import { effectSchema, reactionPackSchema, appliedAckSchema } from './generated.ts';
export const framingSchema = z.object({ subject_id: z.string().regex(/^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$/), rules: z.array(z.enum(['subject','fixed','hold'])).min(1).max(3).refine(r => new Set(r).size === r.length, 'Rules must be unique'), ttl_ms: z.number().int().min(1).max(600) }).strict();
export const savedSchema = z.object({ effect: effectSchema, pack: reactionPackSchema, framing: framingSchema, binding: z.enum(['liquidation','viewer-reaction','unbound']) }).strict();
export const stateSchema = z.object({ mode: z.literal('fixture'), origin: z.literal('synthetic-local'), owner: z.literal('fixture-owner'), epoch: z.string(), revision: z.number().int().nonnegative(), health: z.enum(['fresh','stale']), applied: effectSchema, previous: effectSchema.nullable(), saved: savedSchema.nullable(), receipt: appliedAckSchema.nullable(), run: z.enum(['idle','previewed','cancelled']) }).strict();
export const timelineSchema = z.array(z.object({ id: z.string(), start_ms: z.number(), end_ms: z.number(), status: z.enum(['would_apply','skipped','would_cancel_pack','cancelled']), reason: z.string() }).strict());
export const previewSchema = z.object({ mode: z.literal('fixture'), dispatch: z.literal(false), effect: effectSchema.optional(), horizon_ms: z.number().optional(), timeline: timelineSchema.optional() }).strict();
export const writeSchema = z.object({ epoch: z.string(), revision: z.number().int().nonnegative(), effect: effectSchema.optional(), saved: savedSchema.optional(), pack: reactionPackSchema.optional(), scenario: z.enum(['stale','disconnect','fresh']).optional() }).strict();
export type State = z.infer<typeof stateSchema>;
export type Saved = z.infer<typeof savedSchema>;
export type Framing = z.infer<typeof framingSchema>;
export type Preview = z.infer<typeof previewSchema>;
export type Write = z.infer<typeof writeSchema>;
export type Page = 'effects' | 'reactions' | 'framing';
export const initialFraming: Framing = { subject_id: 'object-furbomek', rules: ['subject','fixed'], ttl_ms: 500 };

export function sameEffect(left: Effect, right: Effect): boolean {
  const fields = (effect: Effect) => Object.entries(effect).sort(([a], [b]) => a.localeCompare(b));
  return JSON.stringify(fields(left)) === JSON.stringify(fields(right));
}
