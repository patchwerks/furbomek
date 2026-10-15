shader_type canvas_item;
render_mode unshaded;

uniform sampler2D optical_image : filter_linear;
uniform vec4 source_crop = vec4(0.2, 0.2, 0.6, 0.6);
uniform int palette_index = 1;
uniform float point_pixels = 1.45;
uniform vec4 subject_box = vec4(-2.0, -2.0, 0.0, 0.0);

void fragment() {
	vec2 uv = source_crop.xy + UV * source_crop.zw;
	vec3 optical = texture(optical_image, uv).rgb;
	vec2 texel = 1.0 / vec2(textureSize(optical_image, 0));
	float luma = dot(optical, vec3(0.2126, 0.7152, 0.0722));
	vec3 weights = vec3(0.2126, 0.7152, 0.0722);
	float lx = dot(texture(optical_image, uv + vec2(texel.x * 3.0, 0.0)).rgb, weights);
	float rx = dot(texture(optical_image, uv - vec2(texel.x * 3.0, 0.0)).rgb, weights);
	float ty = dot(texture(optical_image, uv + vec2(0.0, texel.y * 3.0)).rgb, weights);
	float by = dot(texture(optical_image, uv - vec2(0.0, texel.y * 3.0)).rgb, weights);
	float range = max(max(lx, rx), max(ty, by)) - min(min(lx, rx), min(ty, by));
	float edge = smoothstep(0.02, 0.18, length(vec2(lx - rx, ty - by)));
	float contrast = smoothstep(0.02, 0.13, range);
	float dark_detail = smoothstep(0.01, 0.065, range) * (1.0 - smoothstep(0.20, 0.50, luma));
	vec2 border = min(uv - subject_box.xy, subject_box.xy + subject_box.zw - uv);
	float subject = smoothstep(-0.018, 0.018, min(border.x, border.y)) * (1.0 - smoothstep(0.20, 0.65, luma));
	vec2 grid = FRAGCOORD.xy / vec2(point_pixels * 1.38, point_pixels * 1.08);
	vec2 cell = floor(grid);
	float seed = fract(sin(dot(cell, vec2(12.9898, 78.233))) * 43758.5453);
	vec2 p = abs(fract(grid) - vec2(0.5) + vec2(seed - 0.5, fract(seed * 7.1) - 0.5) * 0.62);
	float stroke = (1.0 - smoothstep(0.31, 0.48, p.x)) * (1.0 - smoothstep(0.17, 0.37, p.y));
	float occupancy = clamp(0.04 + contrast * 0.56 + edge * 0.30 + subject * 0.58 + dark_detail * 0.20, 0.025, 0.96);
	stroke *= step(seed, occupancy);
	float detail = clamp(0.06 + subject * 0.64 + contrast * 0.50 + edge * 0.40 + dark_detail * 0.22, 0.0, 1.0);
	vec3 color = mix(vec3(0.025, 0.001, 0.004), vec3(1.0, 0.055, 0.13), detail);
	if (palette_index == 0) color = optical;
	float vignette = 1.0 - smoothstep(0.40, 0.73, length(UV - vec2(0.5)));
	float environment = smoothstep(0.30, 0.85, luma) * (1.0 - subject);
	vec3 ambient_surface = vec3(0.065, 0.0015, 0.005) * environment * luma;
	COLOR = vec4((color * stroke * mix(0.78, 1.0, seed) + ambient_surface) * vignette, 1.0);
}
