from dishka import Provider, Scope, provide

from src.infrastructure.database.ladybug.repository import LadybugGraphRepository
from src.infrastructure.database.postgres.types import (
    AmlDBSession,
)
from src.infrastructure.storage.csv_store import CsvStore
from src.infrastructure.storage.graph_artifacts import GraphArtifactStore
from src.modules.graph.repositories.graph import GraphStoreRepository
from src.modules.jobs.repositories.job import JobRepository
from src.settings import settings


class RepositoriesProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def job_repository(self, session: AmlDBSession) -> JobRepository:
        return JobRepository(session)

    @provide(scope=Scope.APP)
    def graph_store_repository(self) -> GraphStoreRepository:
        return LadybugGraphRepository(settings.ladybug.db_path)

    @provide(scope=Scope.APP)
    def csv_store(self) -> CsvStore:
        return CsvStore(settings.storage.csv_path)

    @provide(scope=Scope.APP)
    def graph_artifact_store(self) -> GraphArtifactStore:
        return GraphArtifactStore(settings.storage.csv_path)
