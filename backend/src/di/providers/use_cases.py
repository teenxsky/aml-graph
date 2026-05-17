from dishka import Provider, Scope, provide

from src.infrastructure.storage.csv_store import CsvStore
from src.modules.graph.repositories.graph import GraphStoreRepository
from src.modules.graph.use_cases.process_ibm_graph_pipeline import ProcessIbmGraphPipelineUseCase
from src.modules.graph.use_cases.stream_graph import StreamGraphUseCase
from src.modules.jobs.repositories.job import JobRepository
from src.modules.jobs.use_cases.upload_graph import UploadGraphUseCase

__all__ = ['UseCasesProvider']


class UseCasesProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def stream_graph_use_case(
        self,
        job_repository: JobRepository,
        graph_store_repository: GraphStoreRepository,
    ) -> StreamGraphUseCase:
        return StreamGraphUseCase(job_repository, graph_store_repository)

    @provide(scope=Scope.REQUEST)
    def upload_graph_use_case(
        self,
        job_repository: JobRepository,
        csv_store: CsvStore,
    ) -> UploadGraphUseCase:
        return UploadGraphUseCase(job_repository, csv_store)

    @provide(scope=Scope.REQUEST)
    def process_ibm_graph_pipeline_use_case(self) -> ProcessIbmGraphPipelineUseCase:
        return ProcessIbmGraphPipelineUseCase()
