import io

from app.vendors.application.commands.create_vendor import CreateVendorCommand, CreateVendorUseCase
from app.vendors.application.commands.upload_w9_document import (
    UploadW9DocumentCommand,
    UploadW9DocumentUseCase,
)
from tests.fakes.fake_ports import FakeFileStorage
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_upload_w9_document_stores_file_and_records_reference_on_vendor() -> None:
    uow = FakeUnitOfWork()
    file_storage = FakeFileStorage()

    vendor = await CreateVendorUseCase(uow).execute(
        CreateVendorCommand(
            legal_name="Acme Supplies",
            contact_email="ap@acme.com",
            tax_id="12-3456789",
            street="1 Main St",
            city="Springfield",
            state="IL",
            postal_code="62701",
        )
    )

    use_case = UploadW9DocumentUseCase(uow, file_storage, container_name="documents")
    updated = await use_case.execute(
        UploadW9DocumentCommand(
            vendor_id=vendor.id,
            filename="w9.pdf",
            content=io.BytesIO(b"%PDF-fake-content"),
            content_type="application/pdf",
        )
    )

    assert updated.w9_document_reference == f"documents/vendors/{vendor.id}/w9/w9.pdf"
    assert file_storage.uploaded[f"documents/vendors/{vendor.id}/w9/w9.pdf"] == b"%PDF-fake-content"

    # Now that a W-9 is on file, activation should succeed.
    updated.activate()
    assert updated.is_active
