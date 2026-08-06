from app.schemas.health import HealthResponse


class HealthService:
    def __init__(self, *, version: str) -> None:
        self._version = version

    def get_health(self) -> HealthResponse:
        return HealthResponse(version=self._version)
