"""Product Recommendation API routes."""

from fastapi import APIRouter, Depends, status

from app.dependencies import get_product_recommendation_service
from app.ml.product_recommendation.recommendation_service import ProductRecommendationService
from app.schemas.product_recommendation import (
    ProductCatalogResponse,
    ProductRecommendRequest,
    ProductRecommendResponse,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ml/products", tags=["Product Recommendation"])


@router.get(
    "/catalog",
    response_model=ProductCatalogResponse,
    summary="Get lending product catalogue",
    description="Returns all lending products with eligibility criteria.",
)
def get_product_catalog(
    service: ProductRecommendationService = Depends(get_product_recommendation_service),
) -> ProductCatalogResponse:
    return service.get_catalog()


@router.post(
    "/recommend",
    response_model=ProductRecommendResponse,
    status_code=status.HTTP_200_OK,
    summary="Recommend lending products",
    description=(
        "Hybrid business-rule + ML ranking using Customer360/External profile "
        "and Repayment Capacity model output. Returns top product recommendations."
    ),
)
def recommend_products(
    request: ProductRecommendRequest,
    service: ProductRecommendationService = Depends(get_product_recommendation_service),
) -> ProductRecommendResponse:
    result = service.recommend(request)
    logger.info(
        "Product recommendation profile_id=%s top=%s",
        result.profile_id,
        result.top_recommendation,
    )
    return result
