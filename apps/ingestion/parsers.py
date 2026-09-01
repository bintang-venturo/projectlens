from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass
class ParsedPage:
    content: str
    source: str
    page_number: int


class DocumentParser(ABC):

    @abstractmethod
    def parse(self, file_path: str) -> list[ParsedPage]:
        ...


class PDFParser(DocumentParser):

    def parse(self, file_path: str) -> list[ParsedPage]:
        source = Path(file_path).name
        pages: list[ParsedPage] = []
        doc = fitz.open(file_path)
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                pages.append(ParsedPage(
                    content=text,
                    source=source,
                    page_number=page_num + 1,
                ))
        finally:
            doc.close()
        return pages
