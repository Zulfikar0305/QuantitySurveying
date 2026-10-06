from dataclasses import dataclass
from typing import Tuple, Union, Optional
import math

from ..pdf_processing.geometry_models import Point


@dataclass(frozen=True)
class CoordinateMapper:
    zoom: float
    offset_x: float
    offset_y: float
    page_width: float
    page_height: float
    page_rotation: int = 0
    
    def __post_init__(self):
        if self.zoom <= 0:
            raise ValueError(f"Zoom must be positive, got {self.zoom}")
        if self.page_width <= 0:
            raise ValueError(f"Page width must be positive, got {self.page_width}")
        if self.page_height <= 0:
            raise ValueError(f"Page height must be positive, got {self.page_height}")
        if self.page_rotation not in (0, 90, 180, 270):
            raise ValueError(f"Page rotation must be 0, 90, 180, or 270, got {self.page_rotation}")
    
    @property
    def is_rotated(self) -> bool:
        return self.page_rotation != 0
    
    def page_to_screen(self, page_point: Union[Tuple[float, float], "Point"]) -> Tuple[float, float]:
        px, py = self._extract_coords(page_point)
        if self.page_rotation == 90:
            screen_x = py * self.zoom + self.offset_x
            screen_y = (self.page_width - px) * self.zoom + self.offset_y
        elif self.page_rotation == 180:
            screen_x = (self.page_width - px) * self.zoom + self.offset_x
            screen_y = (self.page_height - py) * self.zoom + self.offset_y
        elif self.page_rotation == 270:
            screen_x = (self.page_height - py) * self.zoom + self.offset_x
            screen_y = px * self.zoom + self.offset_y
        else:
            screen_x = px * self.zoom + self.offset_x
            screen_y = py * self.zoom + self.offset_y
        return (screen_x, screen_y)
    
    def screen_to_page(self, screen_point: Union[Tuple[float, float], "Point"]) -> Tuple[float, float]:
        sx, sy = self._extract_coords(screen_point)
        if self.page_rotation == 90:
            py = (sx - self.offset_x) / self.zoom
            px = self.page_width - (sy - self.offset_y) / self.zoom
        elif self.page_rotation == 180:
            px = self.page_width - (sx - self.offset_x) / self.zoom
            py = self.page_height - (sy - self.offset_y) / self.zoom
        elif self.page_rotation == 270:
            px = (sy - self.offset_y) / self.zoom
            py = self.page_height - (sx - self.offset_x) / self.zoom
        else:
            px = (sx - self.offset_x) / self.zoom
            py = (sy - self.offset_y) / self.zoom
        return (px, py)
    
    def page_rect_to_screen(self, x0: float, y0: float, x1: float, y1: float) -> Tuple[float, float, float, float]:
        tl = self.page_to_screen((x0, y0))
        br = self.page_to_screen((x1, y1))
        return (tl[0], tl[1], br[0], br[1])
    
    def screen_rect_to_page(self, x0: float, y0: float, x1: float, y1: float) -> Tuple[float, float, float, float]:
        tl = self.screen_to_page((x0, y0))
        br = self.screen_to_page((x1, y1))
        return (tl[0], tl[1], br[0], br[1])
    
    def page_point_within_page(self, page_x: float, page_y: float) -> bool:
        return 0 <= page_x <= self.page_width and 0 <= page_y <= self.page_height
    
    def screen_point_within_viewport(self, screen_x: float, screen_y: float) -> bool:
        left = self.offset_x
        right = self.offset_x + self.page_width * self.zoom
        top = self.offset_y
        bottom = self.offset_y + self.page_height * self.zoom
        return left <= screen_x <= right and top <= screen_y <= bottom
    
    def to_dict(self) -> dict:
        return {
            "zoom": self.zoom,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "page_width": self.page_width,
            "page_height": self.page_height,
            "page_rotation": self.page_rotation
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CoordinateMapper":
        return cls(
            zoom=float(data["zoom"]),
            offset_x=float(data["offset_x"]),
            offset_y=float(data["offset_y"]),
            page_width=float(data["page_width"]),
            page_height=float(data["page_height"]),
            page_rotation=int(data.get("page_rotation", 0))
        )
    
    def _extract_coords(self, point: Union[Tuple[float, float], "Point"]) -> Tuple[float, float]:
        if isinstance(point, tuple):
            return point
        return (point.x, point.y)
    
    def __repr__(self) -> str:
        return (
            f"CoordinateMapper(zoom={self.zoom:.2f}, offset=({self.offset_x:.1f}, {self.offset_y:.1f}), "
            f"page=({self.page_width:.1f}x{self.page_height:.1f}), rotation={self.page_rotation})"
        )
