from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image, ImageDraw, ImageFont

from kartli.models import Area, Coord, Line, Marker
from kartli.rendering.projection import (
    Projection,
    ground_resolution,
    snap_to_standard_scale,
)


class Overlay(ABC):
    """Abstract base for anything drawn on top of the tile layer."""

    @abstractmethod
    def draw(
        self,
        image: Image.Image,
        origin_x: float,
        origin_y: float,
        zoom: int,
        tile_size: int,
        projection: Projection,
    ) -> None:
        ...


def _coord_to_canvas(
    coord: Coord,
    origin_x: float,
    origin_y: float,
    zoom: int,
    tile_size: int,
    projection: Projection,
) -> tuple[int, int]:
    px, py = projection.coord_to_pixel(coord, zoom, tile_size)
    return int(px - origin_x), int(py - origin_y)


def _get_font(size: int = 12) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                size,
            )
        except OSError:
            try:
                return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
            except OSError:
                return ImageFont.load_default()


def _draw_text_with_outline(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str = "black",
    outline_color: str = "white",
    outline_width: int = 2,
) -> None:
    x, y = xy
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw.text(xy, text, font=font, fill=fill)


def _parse_color_with_alpha(color: str, alpha: int) -> tuple[int, int, int, int]:
    from PIL import ImageColor

    rgb = ImageColor.getrgb(color)
    if len(rgb) == 4:
        return rgb  # type: ignore[return-value]
    return (*rgb, alpha)


class MarkerOverlay(Overlay):
    def __init__(self, marker: Marker):
        self.marker = marker

    def draw(
        self,
        image: Image.Image,
        origin_x: float,
        origin_y: float,
        zoom: int,
        tile_size: int,
        projection: Projection,
    ) -> None:
        cx, cy = _coord_to_canvas(
            self.marker.coord, origin_x, origin_y, zoom, tile_size, projection
        )
        draw = ImageDraw.Draw(image)
        r = self.marker.size
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=self.marker.color,
            outline="white",
            width=2,
        )
        if self.marker.label:
            font = _get_font(13)
            _draw_text_with_outline(
                draw,
                (cx + r + 4, cy - r),
                self.marker.label,
                font=font,
                fill="black",
            )


class AreaOverlay(Overlay):
    def __init__(self, area: Area):
        self.area = area

    def draw(
        self,
        image: Image.Image,
        origin_x: float,
        origin_y: float,
        zoom: int,
        tile_size: int,
        projection: Projection,
    ) -> None:
        points = [
            _coord_to_canvas(c, origin_x, origin_y, zoom, tile_size, projection)
            for c in self.area.coords
        ]
        if len(points) < 3:
            return

        alpha = int(self.area.opacity * 255)
        fill_rgba = _parse_color_with_alpha(self.area.fill_color, alpha)
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.polygon(points, fill=fill_rgba)

        image.alpha_composite(overlay)

        draw = ImageDraw.Draw(image)
        stroke_rgba = _parse_color_with_alpha(self.area.stroke_color, 200)
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            draw.line([p1, p2], fill=stroke_rgba, width=self.area.stroke_width)

        if self.area.label:
            cx = sum(p[0] for p in points) // len(points)
            cy = sum(p[1] for p in points) // len(points)
            font = _get_font(13)
            _draw_text_with_outline(
                draw, (cx, cy), self.area.label, font=font, fill="black"
            )


class LineOverlay(Overlay):
    def __init__(self, line: Line):
        self.line = line

    def draw(
        self,
        image: Image.Image,
        origin_x: float,
        origin_y: float,
        zoom: int,
        tile_size: int,
        projection: Projection,
    ) -> None:
        if len(self.line.coords) < 2:
            return
        points = [
            _coord_to_canvas(c, origin_x, origin_y, zoom, tile_size, projection)
            for c in self.line.coords
        ]
        draw = ImageDraw.Draw(image)
        draw.line(points, fill=self.line.color, width=self.line.width, joint="curve")


_NICE_DISTANCES = [
    10, 20, 50, 100, 200, 500,
    1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000, 200_000, 500_000,
]


def _format_distance(meters: float) -> str:
    if meters >= 1_000:
        km = meters / 1_000
        return f"{km:g} km"
    return f"{meters:g} m"


class ScaleBarOverlay(Overlay):
    """Draws a scale bar in the bottom-left corner with the current map scale."""

    def __init__(self, target_width_px: int = 150):
        self._target_width = target_width_px

    def draw(
        self,
        image: Image.Image,
        origin_x: float,
        origin_y: float,
        zoom: int,
        tile_size: int,
        projection: Projection,
    ) -> None:
        img_w, img_h = image.size

        center_y = origin_y + img_h / 2
        center_coord = projection.pixel_to_coord(
            origin_x + img_w / 2, center_y, zoom, tile_size
        )
        m_per_px = ground_resolution(center_coord.lat, zoom, tile_size)

        target_meters = self._target_width * m_per_px
        bar_meters = _NICE_DISTANCES[0]
        for d in _NICE_DISTANCES:
            if d <= target_meters:
                bar_meters = d
            else:
                break

        bar_px = int(bar_meters / m_per_px)
        if bar_px < 20:
            bar_px = 20

        scale_denom = snap_to_standard_scale(center_coord.lat, zoom, tile_size)

        margin = 15
        bar_height = 6
        x0 = margin
        y0 = img_h - margin - bar_height - 20

        bg_pad = 8
        font = _get_font(11)
        distance_text = _format_distance(bar_meters)
        scale_text = f"1:{scale_denom:,}".replace(",", "'")

        label_bbox = font.getbbox(scale_text)
        label_w = label_bbox[2] - label_bbox[0]
        bg_w = max(bar_px, label_w) + bg_pad * 2

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rounded_rectangle(
            [x0 - bg_pad, y0 - bg_pad - 14, x0 + bg_w, y0 + bar_height + 20 + bg_pad],
            radius=4,
            fill=(255, 255, 255, 200),
        )
        image.alpha_composite(overlay)

        draw = ImageDraw.Draw(image)

        draw.text((x0, y0 - 14), scale_text, font=font, fill=(80, 80, 80))

        draw.rectangle(
            [x0, y0, x0 + bar_px, y0 + bar_height],
            fill=(60, 60, 60),
            outline=(40, 40, 40),
        )

        draw.text(
            (x0, y0 + bar_height + 3),
            distance_text,
            font=font,
            fill=(60, 60, 60),
        )


def build_overlays(
    markers: list[Marker],
    areas: list[Area],
    lines: list[Line],
) -> list[Overlay]:
    overlays: list[Overlay] = []
    for a in areas:
        overlays.append(AreaOverlay(a))
    for ln in lines:
        overlays.append(LineOverlay(ln))
    for m in markers:
        overlays.append(MarkerOverlay(m))
    return overlays
