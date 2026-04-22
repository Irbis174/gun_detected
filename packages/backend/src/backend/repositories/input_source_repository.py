from backend.db.models import InputSourceModel
from backend.db.session import session_scope
from backend.domain.input_source import InputSource


def _to_domain(source: InputSourceModel) -> InputSource:
    return InputSource(
        source_id=source.source_id,
        name=source.name,
        source_type=source.source_type,
        source=source.source,
        connected=source.connected,
    )


class InputSourceRepository:
    def add(self, source: InputSource) -> InputSource:
        with session_scope() as session:
            model = InputSourceModel(
                name=source.name,
                source_type=source.source_type,
                source=source.source,
                connected=source.connected,
            )
            session.add(model)
            session.flush()
            source.source_id = model.source_id
            return source

    def list(self) -> list[InputSource]:
        with session_scope() as session:
            models = (
                session.query(InputSourceModel)
                .order_by(InputSourceModel.source_id)
                .all()
            )
            return [_to_domain(model) for model in models]

    def get(self, id: int) -> InputSource | None:
        with session_scope() as session:
            model = session.get(InputSourceModel, id)
            if model is None:
                return None
            return _to_domain(model)

    def delete(self, id: int) -> InputSource | None:
        with session_scope() as session:
            model = session.get(InputSourceModel, id)
            if model is None:
                return None

            source = _to_domain(model)
            session.delete(model)
            return source


source_repo = InputSourceRepository()
