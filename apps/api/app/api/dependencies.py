from typing import Annotated

from fastapi import Depends, Request

from app.services.health import HealthService
from app.services.readiness import DatabaseReadinessService, ReadinessService


def get_health_service(request: Request) -> HealthService:
    return HealthService(version=request.app.state.settings.app_version)


def get_readiness_service(request: Request) -> ReadinessService:
    return DatabaseReadinessService(
        session_factory=request.app.state.session_factory,
        version=request.app.state.settings.app_version,
    )


HealthServiceDependency = Annotated[HealthService, Depends(get_health_service)]
ReadinessServiceDependency = Annotated[ReadinessService, Depends(get_readiness_service)]
