import { framingPresetSchema } from './liveGenerated.ts';
import type { FramingPreset } from './liveGenerated.ts';

/** Immediate form feedback only; the owner controller remains authoritative. */
export function framingIssue(value: FramingPreset): string {
  const parsed = framingPresetSchema.safeParse(value);
  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    return issue ? `${issue.path.join('.')}: ${issue.message}` : 'Check framing values.';
  }
  const shots = value.shots;
  if (new Set(shots.map(shot => shot.id)).size !== shots.length || new Set(value.rules.map(rule => rule.id)).size !== value.rules.length) return 'Shot and rule IDs must be unique.';
  if (!shots.some(shot => shot.id === value.default)) return 'Choose an existing default shot.';
  if (!shots.some(shot => shot.id === value.fallback && shot.target.kind === 'fixed')) return 'Choose a fixed fallback shot.';
  for (const shot of shots) {
    if (shot.target.kind === 'fixed') {
      const roi = shot.target.roi;
      if (roi.x + roi.width > 1 || roi.y + roi.height > 1) return `Shot ${shot.id}: crop must fit inside the camera frame.`;
    }
  }
  for (const rule of value.rules) {
    if (!shots.some(shot => shot.id === rule.target)) return `Rule ${rule.id}: choose an existing shot.`;
    if (!shots.some(shot => shot.target.kind !== 'fixed' && shot.target.kind === rule.trigger.subject.kind && shot.target.id === rule.trigger.subject.id)) return `Rule ${rule.id}: choose an approved subject from the shot list.`;
  }
  return '';
}
