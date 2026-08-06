from fastapi import APIRouter, status

from app.api.dependencies import HealthServiceDependency, ReadinessServiceDependency
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health(service: HealthServiceDependency) -> HealthResponse:
    return service.get_health()


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "A required dependency is unavailable."
        }
    },
)
async def ready(service: ReadinessServiceDependency) -> HealthResponse:
    await service.ensure_ready()
    return service.get_status()
