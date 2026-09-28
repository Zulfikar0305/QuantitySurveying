import os
from typing import Optional
import pymupdf

from .geometry_models import (
    PdfDocument, PageGeometry, TextElement, DrawingElement,
    PdfProcessingError, FileNotFoundError, InvalidPdfError,
    EmptyPdfError, PermissionError, Point
)


class PdfProcessor:
    def __init__(self):
        pass
    
    def process_file(self, filepath: str) -> 'PdfDocument':
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)
        if not os.access(filepath, os.R_OK):
            raise PermissionError(filepath)
        try:
            doc = pymupdf.open(filepath)
        except Exception as e:
            if 'permission' in str(e).lower() or 'access' in str(e).lower():
                raise PermissionError(filepath)
            raise InvalidPdfError(filepath, str(e))
        try:
            return self._process_document(doc, filepath)
        finally:
            doc.close()
    
    def process_bytes(self, pdf_bytes: bytes, filename: str = 'unknown.pdf') -> 'PdfDocument':
        doc = pymupdf.open(stream=pdf_bytes, filetype='pdf')
        try:
            return self._process_document(doc, filename)
        finally:
            doc.close()
    
    def _process_document(self, doc, filepath: str) -> 'PdfDocument':
        if len(doc) == 0:
            raise EmptyPdfError(filepath)
        pdf_doc = PdfDocument(filepath=filepath, page_count=len(doc))
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_geometry = self._process_page(page, page_num)
            pdf_doc.pages.append(page_geometry)
        return pdf_doc
    
    def _process_page(self, page, page_index: int):
        from .geometry_models import Rectangle
        page_label = page.get_label() or None
        mediabox = page.mediabox
        cropbox = page.cropbox if page.cropbox != page.mediabox else None
        rotation = page.rotation
        page_size = (float(mediabox.width), float(mediabox.height))
        page_geom = PageGeometry(
            page_index=page_index,
            page_label=page_label,
            page_size=page_size,
            media_box=self._rect_to_model(mediabox),
            crop_box=self._rect_to_model(cropbox) if cropbox else None,
            rotation=rotation
        )
        self._extract_geometry(page, page_geom)
        self._extract_text(page, page_geom)
        return page_geom
    
    def _rect_to_model(self, rect):
        from .geometry_models import Rectangle
        return Rectangle(
            x0=float(rect.x0), y0=float(rect.y0),
            x1=float(rect.x1), y1=float(rect.y1)
        )
    
    def _extract_geometry(self, page, page_geom):
        drawings = page.get_drawings()
        for drawing_dict in drawings:
            try:
                element = DrawingElement.from_drawings_dict(drawing_dict, page_index=page_geom.page_index)
                page_geom.add_vector_element(element)
            except Exception as e:
                print(f'Warning: Could not process drawing element: {e}')
    
    def _extract_text(self, page, page_geom):
        text_dict = page.get_text('dict')
        if text_dict and 'blocks' in text_dict:
            for block in text_dict['blocks']:
                if block.get('type') == 1:
                    continue
                text_block = self._parse_text_block(block, page_geom.page_index)
                if text_block:
                    page_geom.add_text_element(text_block)
    
    def _parse_text_block(self, block, page_index: int):
        from .geometry_models import TextElement, Rectangle
        try:
            bbox = block.get('bbox', [0, 0, 0, 0])
            text = block.get('text', '')
            if not text and 'lines' in block:
                lines = block.get('lines', [])
                text = ' '.join(span.get('text', '') for line in lines for span in line.get('spans', []))
            font_name = None
            font_size = 12.0
            color = None
            if 'lines' in block and block['lines']:
                first_line = block['lines'][0]
                if 'spans' in first_line and first_line['spans']:
                    first_span = first_line['spans'][0]
                    font_name = first_span.get('font')
                    font_size = first_span.get('size', 12.0)
                    color = first_span.get('color')
            return TextElement(
                text=text,
                bbox=Rectangle(x0=float(bbox[0]), y0=float(bbox[1]),
                              x1=float(bbox[2]), y1=float(bbox[3])),
                position=Point(x=float(bbox[0]), y=float(bbox[1])),
                font_name=font_name,
                font_size=float(font_size) if font_size else 12.0,
                color=self._parse_color(color),
                page_index=page_index
            )
        except Exception as e:
            print(f'Warning: Could not parse text block: {e}')
            return None
    
    @staticmethod
    def _parse_color(color_val):
        if color_val is None:
            return None
        if isinstance(color_val, (tuple, list)):
            if len(color_val) >= 3:
                return (float(color_val[0]), float(color_val[1]), float(color_val[2]))
        return None
