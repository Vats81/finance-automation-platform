import asyncio
import uuid

from app.data_import.application.dtos import ImportSummary, ProgressCallback
from app.data_import.application.import_customers import ImportCustomersUseCase
from app.data_import.application.jobs import ImportJobRegistry, ImportJobStatus
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def _wait_until_finished(registry: ImportJobRegistry, job_id: uuid.UUID) -> None:
    for _ in range(200):
        job = registry.get(job_id)
        assert job is not None
        if job.status != ImportJobStatus.RUNNING:
            return
        await asyncio.sleep(0.005)
    raise AssertionError("job never finished")


async def test_job_reports_progress_then_finishes_with_the_summary() -> None:
    registry = ImportJobRegistry()
    gate = asyncio.Event()
    summary = ImportSummary(total_rows=10, created=10, skipped_duplicates=0)

    async def runner(on_progress: ProgressCallback) -> ImportSummary:
        on_progress(4, 10)
        await gate.wait()
        return summary

    business_id = uuid.uuid4()
    job = registry.start(business_id=business_id, total_rows=10, runner=runner)
    await asyncio.sleep(0.01)

    assert job.status == ImportJobStatus.RUNNING
    assert job.processed_rows == 4
    assert registry.running_for_business(business_id) is job
    assert registry.running_for_business(uuid.uuid4()) is None

    gate.set()
    await _wait_until_finished(registry, job.id)

    assert job.status == ImportJobStatus.DONE
    assert job.processed_rows == 10
    assert job.summary == summary
    assert registry.running_for_business(business_id) is None


async def test_a_crashing_import_is_reported_as_failed_not_raised() -> None:
    registry = ImportJobRegistry()

    async def runner(on_progress: ProgressCallback) -> ImportSummary:
        raise RuntimeError("boom")

    job = registry.start(business_id=uuid.uuid4(), total_rows=3, runner=runner)
    await _wait_until_finished(registry, job.id)

    assert job.status == ImportJobStatus.FAILED
    assert job.error is not None and "upload again" in job.error
    assert job.summary is None


async def test_unknown_job_is_none() -> None:
    assert ImportJobRegistry().get(uuid.uuid4()) is None


async def test_importer_reports_progress_for_every_row_and_completion() -> None:
    uow = FakeUnitOfWork()
    rows = [{"Name": "A"}, {"Name": ""}, {"Name": "C"}]
    seen: list[tuple[int, int]] = []

    await ImportCustomersUseCase(uow).execute(
        business_id=uuid.uuid4(),
        rows=rows,
        column_mapping={"name": "Name"},
        on_progress=lambda done, total: seen.append((done, total)),
    )

    assert seen == [(0, 3), (1, 3), (2, 3), (3, 3)]
