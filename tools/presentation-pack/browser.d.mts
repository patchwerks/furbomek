import type { ParsedPack } from '../../packages/extension-preview/index.mjs';

export interface CompanionMetadata {
  readonly metadataVersion: 1;
  readonly packId: string;
  readonly packVersion: string;
  readonly previewContractVersion: 1;
  readonly author: string;
  readonly license: 'MIT' | 'CC0-1.0';
  readonly packSha256: string;
}
export interface BrowserMetadataResult {
  readonly pack: ParsedPack;
  readonly metadata: CompanionMetadata;
  readonly packSha256: string;
}
/** Strict byte-only validation; requires native Web Crypto in a secure browser context. */
export function validateBrowserMetadata(packBytes: Uint8Array, metadataBytes: Uint8Array): Promise<Readonly<BrowserMetadataResult>>;
