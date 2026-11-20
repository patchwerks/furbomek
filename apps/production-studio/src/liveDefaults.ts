import { framingPresetSchema, visualSettingsSchema } from './liveGenerated.ts';

/** Empty authoring drafts, never observed state or permission to dispatch. */
export const createFramingDraft = () => framingPresetSchema.parse({
  id: 'owner-framing', tracking_source: 'owner-tracker',
  shots: [{ id: 'wide', target: { kind: 'fixed', roi: { x: 0, y: 0, width: 1, height: 1 } } }],
  default: 'wide', fallback: 'wide',
});
export const createVisualDraft = () => visualSettingsSchema.parse({});
