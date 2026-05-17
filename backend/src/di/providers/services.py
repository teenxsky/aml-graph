from dishka import Provider, Scope, provide

from src.modules.graph.services.builder import GraphBuilder

__all__ = ['ServicesProvider']


class ServicesProvider(Provider):
    @provide(scope=Scope.APP)
    def get_graph_builder(self) -> GraphBuilder:
        return GraphBuilder()
