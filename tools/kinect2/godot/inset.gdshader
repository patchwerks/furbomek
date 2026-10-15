shader_type canvas_item;
render_mode unshaded;

uniform int style : hint_range(0, 1, 1) = 0;
uniform vec4 source_region = vec4(0.0, 0.0, 1.0, 1.0);

void fragment() {
	vec2 source_uv = source_region.xy + UV * source_region.zw;
	vec4 source = texture(TEXTURE, source_uv);
	float luma = dot(source.rgb, vec3(0.2126, 0.7152, 0.0722));
	if (style == 1) {
		vec3 weights = vec3(0.2126, 0.7152, 0.0722);
		vec2 step_uv = TEXTURE_PIXEL_SIZE * 2.0;
		float lx = dot(texture(TEXTURE, source_uv + vec2(step_uv.x, 0.0)).rgb, weights);
		float rx = dot(texture(TEXTURE, source_uv - vec2(step_uv.x, 0.0)).rgb, weights);
		float ty = dot(texture(TEXTURE, source_uv + vec2(0.0, step_uv.y)).rgb, weights);
		float by = dot(texture(TEXTURE, source_uv - vec2(0.0, step_uv.y)).rgb, weights);
		float range = max(max(lx, rx), max(ty, by)) - min(min(lx, rx), min(ty, by));
		float contrast = smoothstep(0.015, 0.12, range);
		float edge = smoothstep(0.015, 0.16, length(vec2(lx - rx, ty - by)));
		vec2 grid = FRAGCOORD.xy / vec2(2.0, 1.6);
		float seed = fract(sin(dot(floor(grid), vec2(12.9898, 78.233))) * 43758.5453);
		vec2 cell = fract(grid) + vec2(seed - 0.5, fract(seed * 7.1) - 0.5) * 0.62;
		float stroke = step(abs(cell.x - 0.5), 0.38) * step(abs(cell.y - 0.5), 0.28);
		float occupancy = clamp(0.20 + contrast * 0.60 + edge * 0.35 + (1.0 - luma) * 0.10, 0.12, 0.95);
		stroke *= step(seed, occupancy);
		float tone = clamp(0.16 + sqrt(luma) * 0.35 + contrast * 0.55 + edge * 0.35, 0.0, 1.0);
		vec3 crimson = mix(vec3(0.025, 0.001, 0.004), vec3(1.0, 0.08, 0.17), tone);
		COLOR = vec4(crimson * (0.05 * sqrt(luma) + stroke * 0.95), 1.0);
	} else {
		COLOR = vec4(mix(vec3(0.045, 0.01, 0.018), source.rgb, 0.75) * vec3(1.0, 0.56, 0.61), 1.0);
	}
}
