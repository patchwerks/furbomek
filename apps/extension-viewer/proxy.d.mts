/** Public handle of the existing procedural renderer, with no Three.js internals. */
import type { Sample } from '../../packages/extension-preview/index.mjs';
export interface ProxyHandle {
  render(state?: Pick<Sample, 'expression' | 'reaction' | 'reactionProgress'>, reduced?: boolean): void;
  resize(width: number, height: number): void;
  dispose(): void;
}
export function createProxy(canvas: HTMLCanvasElement, onLost: () => void): ProxyHandle;
