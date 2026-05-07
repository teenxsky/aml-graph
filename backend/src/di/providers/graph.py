from dishka import Provider, Scope, provide

from src.di.providers.sessions import SessionStore
from src.graph.builder import GraphBuilder
from src.usecases.stream_graph import StreamGraphUseCase
from src.usecases.upload_graph import UploadGraphUseCase

__all__ = ['GraphProvider']


class GraphProvider(Provider):
    @provide(scope=Scope.APP)
    def get_graph_builder(self) -> GraphBuilder:
        return GraphBuilder()

    @provide(scope=Scope.REQUEST)
    def get_upload_use_case(
        self,
        builder: GraphBuilder,
        session_store: SessionStore,
    ) -> UploadGraphUseCase:
        return UploadGraphUseCase(builder, session_store)

    @provide(scope=Scope.REQUEST)
    def get_stream_use_case(
        self,
        session_store: SessionStore,
    ) -> StreamGraphUseCase:
        return StreamGraphUseCase(session_store)
