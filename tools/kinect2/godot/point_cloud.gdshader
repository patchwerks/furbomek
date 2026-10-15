shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_opaque;

uniform int palette_index : hint_range(0, 2, 1) = 1;
uniform float point_pixels : hint_range(0.75, 2.2, 0.05) = 1.45;
varying vec4 instance_rgba;
varying float cloud_depth;
varying float point_gain;

void vertex() {
	instance_rgba = COLOR;
	cloud_depth = clamp(-MODEL_MATRIX[3].z / 3.0, 0.0, 1.0);
	vec4 clip_center = PROJECTION_MATRIX * VIEW_MATRIX * MODEL_MATRIX[3];
	float seed = fract(sin(float(INSTANCE_ID) * 12.9898) * 43758.5453);
	point_gain = 0.72 + seed * 0.28;
	POSITION = clip_center;
	vec2 pixel_offset = VERTEX.xy * vec2(point_pixels * (1.05 + seed * 0.45), point_pixels * (0.72 + fract(seed * 3.17) * 0.25));
	pixel_offset += vec2(seed - 0.5, fract(seed * 7.31) - 0.5) * 1.25;
	POSITION.xy += pixel_offset * 2.0 / VIEWPORT_SIZE * clip_center.w;
}

void fragment() {
	vec2 p = abs(UV - vec2(0.5)) - vec2(0.42, 0.26);
	float rounded_dash = length(max(p, 0.0)) + min(max(p.x, p.y), 0.0);
	if (rounded_dash > 0.08 || instance_rgba.a < 0.01) discard;
	float luma = dot(instance_rgba.rgb, vec3(0.2126, 0.7152, 0.0722));
	vec3 color = instance_rgba.rgb;
	if (palette_index == 1) color = mix(vec3(0.055, 0.001, 0.005), vec3(0.94, 0.045, 0.10), 0.50 + luma * 0.40 + (1.0 - cloud_depth) * 0.10) * point_gain;
	if (palette_index == 2) color = mix(vec3(0.06, 0.02, 0.13), vec3(0.96, 0.15, 0.22), cloud_depth);
	ALBEDO = color;
	EMISSION = vec3(0.0);
	ALPHA = instance_rgba.a;
}
