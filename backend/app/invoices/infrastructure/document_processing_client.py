import asyncio
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentProcessingResult:
    processed: bool
    confidence: float
    notes: str


class SimulatedDocumentProcessingClient:
    """Stands in for a real OCR/document-intelligence provider (e.g. Azure
    AI Document Intelligence). Line items in this foundation slice are
    entered by the AP clerk at submission time rather than extracted by ML
    (see invoices/application/commands/submit_invoice.py), so this client's
    real job is to represent the async document pipeline stage — virus
    scanning, text indexing, thumbnail generation, confidence scoring —
    that would run regardless of how line items were captured. Swapping in
    a real provider means replacing this class behind the same interface;
    callers (record_ocr_result use case) don't change.
    """

    async def process(self, *, document_reference: str | None) -> DocumentProcessingResult:
        await asyncio.sleep(0.1)  # simulate processing latency

        if document_reference is None:
            return DocumentProcessingResult(
                processed=True, confidence=0.0, notes="No source document attached; skipped OCR pass."
            )
        return DocumentProcessingResult(
            processed=True, confidence=0.98, notes=f"Processed document at {document_reference}."
        )
