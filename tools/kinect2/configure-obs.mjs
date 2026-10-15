import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.env.FURBOMEK_MEDIA_ROOT || '/data/furbomek-media';
const config = join(root, 'obs-config', 'obs-studio');
const tree = execFileSync('xwininfo', ['-root', '-tree'], { encoding: 'utf8' });
const match = tree.match(/(0x[0-9a-f]+) "(Furb-o-Mek Kinect 2 [^"]*)": \("Godot_Engine" "([^"]+)"\)/);
if (!match) throw new Error('Start the Kinect Godot viewer before configuring OBS.');
const selector = `${Number.parseInt(match[1], 16)}\r\n${match[2]}\r\n${match[3]}`;
for (const directory of ['basic/profiles/Kinect2', 'basic/scenes']) {
  mkdirSync(join(config, directory), { recursive: true, mode: 0o700 });
}
const save = (path, data) => {
  if (!existsSync(join(config, path))) writeFileSync(join(config, path), data, { mode: 0o600 });
};
save('global.ini', `[General]\nFirstRun=false\nEnableAutoUpdates=false\n\n[Basic]\nProfile=Kinect2\nProfileDir=Kinect2\nSceneCollection=Kinect2\nSceneCollectionFile=Kinect2\n\n[BasicWindow]\nWarnBeforeStartingStream=true\nWarnBeforeStoppingStream=true\n`);
save('basic/profiles/Kinect2/basic.ini', `[General]\nName=Kinect2\n\n[Video]\nBaseCX=1280\nBaseCY=720\nOutputCX=1280\nOutputCY=720\nFPSType=0\nFPSCommon=30\nScaleType=bicubic\nColorFormat=NV12\nColorSpace=709\nColorRange=Partial\n\n[Output]\nMode=Simple\n\n[SimpleOutput]\nFilePath=${join(root, 'recordings')}\nRecFormat2=mkv\nRecQuality=Small\nRecEncoder=nvenc\nStreamEncoder=nvenc\nVBitrate=6000\nABitrate=160\n\n[Audio]\nSampleRate=48000\nChannelSetup=Stereo\n\n[Hotkeys]\nOBSBasic.StopRecording={"bindings":[{"key":"OBS_KEY_F10"}]}\n`);
const sourceName = 'Kinect2 Point Cloud';
const profilePath = join(config, 'basic/profiles/Kinect2/basic.ini');
const profile = readFileSync(profilePath, 'utf8')
  .replace(/^((?:Base|Output)CX)=\d+$/gm, '$1=1920')
  .replace(/^((?:Base|Output)CY)=\d+$/gm, '$1=1080');
writeFileSync(profilePath, profile, { mode: 0o600 });
const scenePath = join(config, 'basic/scenes/Kinect2.json');
const initialScene = {
  name: 'Kinect2', current_scene: 'Kinect2', current_program_scene: 'Kinect2',
  scene_order: [{ name: 'Kinect2' }],
  sources: [
    { name: sourceName, id: 'xcomposite_input', versioned_id: 'xcomposite_input',
      settings: { capture_window: selector, show_cursor: false, include_border: false,
        exclude_alpha: true, cut_top: 0, cut_left: 0, cut_right: 0, cut_bot: 0 },
      enabled: true, volume: 1, muted: false, flags: 0, mixers: 0 },
    { name: 'Kinect2', id: 'scene', versioned_id: 'scene', settings: {
      id_counter: 1, items: [{ name: sourceName, id: 1, visible: true, locked: false,
        pos: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rot: 0, align: 5,
        bounds_type: 0, bounds_align: 0, bounds: { x: 0, y: 0 },
        crop_left: 0, crop_top: 0, crop_right: 0, crop_bottom: 0 }],
    }, enabled: true, volume: 1, muted: false, flags: 0, mixers: 0 },
  ],
};
const scene = existsSync(scenePath) ? JSON.parse(readFileSync(scenePath, 'utf8')) : initialScene;
if (!Array.isArray(scene.sources)) throw new Error('OBS Kinect2 scene has no source list.');
const cloudSource = scene.sources.find(source => source.name === sourceName && source.id === 'xcomposite_input');
if (!cloudSource || typeof cloudSource.settings !== 'object' || cloudSource.settings === null) {
  throw new Error('OBS Kinect2 point-cloud source is missing; refusing to overwrite the collection.');
}
cloudSource.settings.capture_window = selector;
const outputScene = scene.sources.find(source => source.id === 'scene' && source.name === 'Kinect2');
const outputItem = outputScene?.settings?.items?.find(item => item.name === sourceName);
if (!outputItem) throw new Error('Kinect2 scene item is missing; refusing to replace the collection.');
Object.assign(outputItem, { pos: { x: 0, y: 0 }, scale: { x: 1, y: 1 }, rot: 0,
  scale_ref: { x: 1920, y: 1080 }, scale_rel: { x: 1, y: 1 },
  pos_rel: { x: -1920 / 1080, y: -1 }, bounds_rel: { x: 0, y: 0 },
  align: 5, bounds_type: 0, bounds: { x: 0, y: 0 },
  crop_left: 0, crop_top: 0, crop_right: 0, crop_bottom: 0 });
writeFileSync(scenePath, JSON.stringify(scene, null, 2), { mode: 0o600 });
console.log(`Configured isolated OBS Kinect2 scene at ${config}. No stream destination or network control enabled.`);
