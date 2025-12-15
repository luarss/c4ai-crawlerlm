from typing import ClassVar, Literal

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

    VALIDATION_PATTERNS: ClassVar[list[str]] = [
        r"\$\d+\.?\d*",  # price
        r"\d+\.?\d*\s*(USD|EUR|GBP)",  # price with currency
        r"rating:\s*\d+(\.\d+)?",  # rating
        r"\d+(\.\d+)?\s*star",  # star rating
        r"★+",  # star symbols
    ]


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

    VALIDATION_PATTERNS: ClassVar[list[str]] = [
        r"\d+\s*(cup|tablespoon|teaspoon|ounce|pound|gram|ml|tsp|tbsp|oz|lb|g)",  # ingredient measurements
        r"\d+/\d+",  # fractions
        r"\d+\s*(large|medium|small|whole)",  # counts
        r"(preheat|mix|stir|cook|bake|add|combine|heat|blend|whisk|pour|chop|slice|dice)",  # cooking verbs
        r"\d+\s*(min|minute|hour|hr)s?",  # timing
        r"(serves?|yield|makes?)\s*:?\s*\d+",  # servings
    ]


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

    VALIDATION_PATTERNS: ClassVar[list[str]] = [
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",  # dates: 12/15/2025, 12-15-25
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}",  # Dec 15, January 1
        r"\d{1,2}:\d{2}\s*(AM|PM|am|pm)",  # time: 6:00 PM, 14:30
        r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,",  # day of week: Monday, Tue,
        r"(location|venue|address):",  # location indicators
        r"(online|virtual|remote|in-person|hybrid)",  # event type
        r"(organiz|host|presented by)",  # organizer indicators
        r"\d+\s*(attendee|going|interested|registered)",  # attendee count
        r"(free|sold out|\$\d+)",  # price indicators
        r"(RSVP|register|ticket|admission)",  # event-specific terms
    ]


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

    VALIDATION_PATTERNS: ClassVar[list[str]] = [
        r"\$\d+",  # price: $10, $99
        r"\d+\s*(USD|EUR|GBP|CAD)",  # price with currency
        r"(free|trial|custom pricing|contact sales)",  # free/custom tiers
        r"(/month|/year|/mo|/yr|monthly|yearly|annually|per month|per year)",  # billing period
        r"(basic|pro|premium|enterprise|starter|business|team|individual)",  # common plan names
        r"(feature|includes?|what's included)",  # feature list indicators
        r"(unlimited|limited|\d+\s*(user|GB|TB|project|API call))",  # feature quantifiers
        r"(tier|plan|pricing|subscription|package)",  # pricing table indicators
        r"(billed|charged|payment|invoice)",  # billing terms
        r"(most popular|recommended|best value)",  # plan highlights
    ]


class JobPostingSchema(BaseModel):
    type: Literal["job_posting"]
    title: str
    company: str
    location: str
    department: str | None = None
    posted_date: str | None = None
    employment_type: str | None = None
    description: str | None = None

    VALIDATION_PATTERNS: ClassVar[list[str]] = [
        r"(engineer|developer|manager|designer|analyst|scientist|director|lead|senior|junior)",  # job titles
        r"(full-?time|part-?time|contract|temporary|intern|internship)",  # employment type
        r"(remote|hybrid|on-?site|in-office|work from home)",  # work location type
        r"[A-Z][a-z]+,\s*[A-Z]{2}",  # location: City, ST format
        r"(department|team|division):",  # department indicators
        r"(posted|updated)\s*(on|:)?\s*\d",  # posted date indicators
        r"(\d+\s*days?|week|month)\s*ago",  # relative dates: "3 days ago"
        r"(position|role|job|career|opportunity)",  # job posting terms
        r"(apply|application|candidate|applicant)",  # application terms
        r"(company|organization|employer):",  # company indicators
        r"(salary|compensation|pay|benefits)",  # compensation mentions (rare but useful)
        r"(requirement|qualification|experience|skill)",  # job requirements
    ]


class PersonSchema(BaseModel):
    type: Literal["person"]
    name: str
    title: str | None = None
    bio: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    image_url: str | None = None

    VALIDATION_PATTERNS: ClassVar[list[str]] = [
        r"(professor|dr\.|ph\.?d|researcher|scientist|faculty|lecturer|instructor)",  # academic titles
        r"(engineer|developer|designer|manager|director|VP|CEO|CTO|founder)",  # professional titles
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # email address
        r"\(\d{3}\)\s*\d{3}-\d{4}",  # phone: (555) 123-4567
        r"\d{3}-\d{3}-\d{4}",  # phone: 555-123-4567
        r"linkedin\.com/(in|pub)/",  # LinkedIn profile URL
        r"(biography|bio|about|profile|background):",  # bio section indicators
        r"(education|degree|university|college)",  # educational background
        r"(research|publication|interest|expertise|specialization)",  # academic/professional interests
        r"(contact|email|phone|office|reach):",  # contact information indicators
        r"(title|position|role):",  # title/position indicators
        r"(department|division|group|lab|team):",  # organizational affiliation
    ]


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


def get_validation_patterns(fragment_type: str) -> dict:
    """Get validation patterns for a fragment type from its schema."""
    schema = get_schema(fragment_type)
    return getattr(schema, "VALIDATION_PATTERNS", {})
