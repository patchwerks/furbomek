# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["opencv-contrib-python-headless==4.11.0.86", "numpy==1.26.4"]
# ///
# How to run: uv run --frozen --project tools/motion-lab python tools/motion-lab/print_tags.py
"""Generate an A4 metric vector board; real printer scale requires measurement."""

from pathlib import Path

import cv2


def tag_sheet() -> str:
    """Encode OpenCV dictionary cells at exact millimetre geometry."""
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">',
        "<title>Furb-o-Mek calibration reference and chassis target</title>",
        '<rect width="210" height="297" fill="white"/>',
        '<g font-family="sans-serif" fill="black">',
        '<text x="15" y="15" font-size="5">Calibration board · ArUco 4x4_50</text>',
        '<text x="15" y="23" font-size="3.5">A4 · print actual size / 100% · disable fit to page</text>',
        '<text x="15" y="29" font-size="3.5">Measure all black squares: 40 mm ± 0.25 mm.</text>',
    ]
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    positions = ((0, 25, 40), (1, 145, 40), (2, 145, 160), (3, 25, 160), (10, 85, 233))
    for marker_id, x, y in positions:
        bits = cv2.aruco.generateImageMarker(dictionary, marker_id, 6)
        lines.append(f'<g id="tag-{marker_id}" transform="translate({x} {y})">')
        lines.extend(
            f'<rect x="{column * 40 / 6:.9f}" y="{row * 40 / 6:.9f}" width="{40 / 6:.9f}" height="{40 / 6:.9f}"/>'
            for row in range(6)
            for column in range(6)
            if bits[row, column] == 0
        )
        lines.append("</g>")
        lines.append(
            f'<text x="{x}" y="{y + 46}" font-size="3.5">ID {marker_id}</text>'
        )
    lines.extend(
        [
            '<text x="70" y="105" font-size="3.5">0 → 1 centers: 120 mm</text>',
            '<text x="70" y="112" font-size="3.5">0 → 3 centers: 120 mm</text>',
            '<text x="70" y="119" font-size="3.5">Origin: ID 0 center</text>',
            '<text x="70" y="126" font-size="3.5">x right · y down · z into board</text>',
            '<text x="70" y="133" font-size="3.5">Raised target: negative z</text>',
            '<path d="M15 215H195" stroke="black" stroke-dasharray="2 2"/>',
            '<text x="15" y="223" font-size="3.5">Cut below dashed line only. Mount ID 10 rigidly on chassis.</text>',
            '<path d="M15 284H115M15 281V287M115 281V287" stroke="black" stroke-width="0.3"/>',
            '<text x="125" y="285" font-size="3.5">100 mm scale check</text>',
            "</g></svg>",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    _ = (Path(__file__).parent / "fixtures" / "tag-sheet-a4.svg").write_text(
        tag_sheet()
    )
