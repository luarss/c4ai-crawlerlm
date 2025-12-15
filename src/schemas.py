from typing import Literal

from pydantic import BaseModel, Field


# Supporting Schemas
class PriceSchema(BaseModel):
    current: float
    original: float | None = None
    currency: str = "USD"


class RatingSchema(BaseModel):
    score: float = Field(ge=0, le=5)
    review_count: int = Field(ge=0)


# Main Schemas
class ProductSchema(BaseModel):
    type: Literal["product"]
    name: str
    brand: str | None = None
    price: PriceSchema
    rating: RatingSchema | None = None
    description: str | None = None
    availability: Literal["in_stock", "out_of_stock", "pre_order", "limited"] | None = None
    image_url: str | None = None


class ReviewSchema(BaseModel):
    type: Literal["review"]
    reviewer_name: str
    reviewer_verified: bool | None = None
    rating: float = Field(ge=0, le=5)
    title: str | None = None
    date: str
    body: str
    helpful_count: int | None = Field(None, ge=0)


class RecipeSchema(BaseModel):
    type: Literal["recipe"]
    name: str
    description: str | None = None
    author: str | None = None
    prep_time: str | None = None
    cook_time: str | None = None
    total_time: str | None = None
    servings: str | None = None
    ingredients: list[str]
    instructions: list[str]
    rating: RatingSchema | None = None


class EventSchema(BaseModel):
    type: Literal["event"]
    title: str
    datetime: str
    location: str | None = None
    venue_name: str | None = None
    price: str | None = None
    organizer: str | None = None
    attendee_count: int | None = Field(None, ge=0)
    description: str | None = None
    event_type: Literal["online", "in_person"] | None = None


class PricingPlanSchema(BaseModel):
    name: str
    price: str
    price_amount: float | None = None
    currency: str | None = None
    billing_period: Literal["month", "year", "one_time"] | None = None
    features: list[str]
    description: str | None = None


class PricingTableSchema(BaseModel):
    type: Literal["pricing_table"]
    plans: list[PricingPlanSchema]


class JobPostingSchema(BaseModel):
    type: Literal["job_posting"]
    title: str
    company: str
    location: str
    department: str | None = None
    posted_date: str | None = None
    employment_type: str | None = None
    description: str | None = None


class PersonSchema(BaseModel):
    type: Literal["person"]
    name: str
    title: str | None = None
    bio: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    image_url: str | None = None


# Negative Schemas
class ErrorPageSchema(BaseModel):
    type: Literal["error_page"]
    error_code: int
    message: str
    description: str


class AuthRequiredSchema(BaseModel):
    type: Literal["auth_required"]
    message: str
    description: str
    content_available: Literal[False] = False


class EmptySPAShellSchema(BaseModel):
    type: Literal["empty_shell"]
    framework: Literal["react", "vue", "angular"] | None = None
    content_available: Literal[False] = False
    reason: Literal["client_side_rendering"] = "client_side_rendering"


SCHEMA_REGISTRY = {
    "product": ProductSchema,
    "review": ReviewSchema,
    "recipe": RecipeSchema,
    "event": EventSchema,
    "pricing_table": PricingTableSchema,
    "job_posting": JobPostingSchema,
    "person": PersonSchema,
    "error_page": ErrorPageSchema,
    "auth_required": AuthRequiredSchema,
    "empty_shell": EmptySPAShellSchema,
}


def get_schema(fragment_type: str) -> type[BaseModel]:
    if fragment_type not in SCHEMA_REGISTRY:
        valid_types = ", ".join(SCHEMA_REGISTRY.keys())
        raise ValueError(f"Unknown fragment type: {fragment_type}. Valid types: {valid_types}")
    return SCHEMA_REGISTRY[fragment_type]
