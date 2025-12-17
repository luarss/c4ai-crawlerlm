from typing import ClassVar, Literal

from pydantic import BaseModel, Field

# =============================================================================
# SUPPORTING SCHEMAS
# =============================================================================


class Rating(BaseModel):
    score: float = Field(ge=0, le=5)
    review_count: int = Field(ge=0)


# =============================================================================
# POSITIVE SCHEMAS (Content extraction targets)
# =============================================================================


class Recipe(BaseModel):
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
    rating: Rating | None = None

    VALIDATION_PATTERNS: ClassVar[list[str]] = [
        r"\d+\s*(cup|tablespoon|teaspoon|ounce|pound|gram|ml|tsp|tbsp|oz|lb|g)",  # ingredient measurements
        r"\d+/\d+",  # fractions
        r"\d+\s*(large|medium|small|whole)",  # counts
        r"(preheat|mix|stir|cook|bake|add|combine|heat|blend|whisk|pour|chop|slice|dice)",  # cooking verbs
        r"\d+\s*(min|minute|hour|hr)s?",  # timing
        r"(serves?|yield|makes?)\s*:?\s*\d+",  # servings
    ]


class Event(BaseModel):
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
        r"(?:[01]?\d|2[0-3]):[0-5]\d(?:\s*(?:AM|PM|am|pm))?",  # time: 6:00 PM, 14:30
        r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,",  # day of week: Monday, Tue,
        r"(location|venue|address):",  # location indicators
        r"(online|virtual|remote|in-person|hybrid)",  # event type
        r"(organiz|host|presented by)",  # organizer indicators
        r"\d+\s*(attendee|going|interested|registered)",  # attendee count
        r"(free|sold out|\$\d+)",  # price indicators
        r"(RSVP|register|ticket|admission)",  # event-specific terms
    ]


class PricingPlan(BaseModel):
    name: str
    price: str
    price_amount: float | None = None
    currency: str | None = None
    billing_period: Literal["month", "year", "one_time"] | None = None
    features: list[str]
    description: str | None = None


class PricingTable(BaseModel):
    type: Literal["pricing_table"]
    plans: list[PricingPlan]

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


class JobPosting(BaseModel):
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


class Person(BaseModel):
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


# =============================================================================
# NEGATIVE SCHEMAS (Error pages, auth walls, empty SPAs)
# =============================================================================


class ErrorPage(BaseModel):
    type: Literal["error_page"]
    error_code: int
    message: str
    description: str

    NEGATIVE_VALIDATION_PATTERNS: ClassVar[list[str]] = [
        r"\b(404|500|503|502|403|429)\b",  # HTTP error codes
        r"(page|content).{0,30}(not found|cannot be found|can't be found|unavailable|doesn't exist)",
        r"(error|oops|sorry|uh oh).{0,30}(occurred|happened|wrong|found)",
        r"something (went )?wrong",
        r"the (page|url|link|resource).{0,30}(you|your).{0,30}(looking for|requested|tried to access)",
        r"(broken|dead|invalid).{0,30}(link|url|page)",
        r"(sorry|apologies|we apologize)",
        r"(return|go back).{0,30}(home|homepage)",
        r"error.{0,20}(code|message|details)",
        r"server.{0,20}(error|unavailable|down)",
        r"temporarily unavailable",
        r"under maintenance",
        r"(too many|rate limit).{0,20}(request|attempt)",
        r"please (try again|wait).{0,20}(later|moment|shortly)",
        r"slow down",
    ]


class AuthRequired(BaseModel):
    type: Literal["auth_required"]
    message: str
    description: str
    content_available: Literal[False] = False

    NEGATIVE_VALIDATION_PATTERNS: ClassVar[list[str]] = [
        # Login form indicators
        r'type\s*=\s*["\']password["\']',  # password input field
        r"(log\s*in|sign\s*in)\s*(with|using)?\s*(google|facebook|apple|github|twitter)",  # social login
        r"forgot.{0,20}password",  # forgot password link
        r"(don't|do not).{0,20}have.{0,20}account",  # signup prompt
        r"(create|register).{0,20}account",  # account creation
        r"(email|username).{0,20}(and|&).{0,20}password",  # login field labels
        # Access control messages
        r"(sign|log).{0,10}(in|up).{0,30}(to|for).{0,30}(continue|access|view|read|see)",
        r"(subscription|member|premium).{0,30}(required|only|exclusive)",
        r"(paywall|pay.{0,5}wall)",
        r"(unlock|subscribe).{0,30}(to|for).{0,30}(read|view|access|continue)",
        r"(exclusive|premium).{0,30}(content|access|member)",
        r"(limited|restricted).{0,30}access",
        r"access.{0,20}(denied|restricted|requires)",
        # Auth buttons/CTAs
        r"(continue|proceed).{0,20}with.{0,20}(google|facebook|apple|email)",
        r"already.{0,20}have.{0,20}account",
    ]


class EmptySPAShell(BaseModel):
    type: Literal["empty_shell"]
    framework: Literal["react", "vue", "angular"] | None = None
    content_available: Literal[False] = False
    reason: Literal["client_side_rendering"] = "client_side_rendering"

    NEGATIVE_VALIDATION_PATTERNS: ClassVar[list[str]] = [
        # Framework markers
        r'id\s*=\s*["\'](__next|root|app|__nuxt)["\']',  # React/Next/Vue/Nuxt root divs
        r"data-react(id|-root|-helmet)",  # React markers
        r"ng-(version|app|controller|cloak)",  # Angular markers
        r"__NEXT_DATA__|__nuxt|__NUXT__",  # Framework data injection
        r"_reactRoot|_reactListening",  # React internal properties
        # JavaScript requirement messages
        r"javascript\s*(is\s*)?(required|disabled|not enabled|turned off)",
        r"enable\s*javascript\s*(to|in).{0,30}(view|use|see|run|access)",
        r"(please|you must|you need to)\s*enable\s*javascript",
        r"this (site|app|application).{0,30}requires.{0,30}javascript",
        r"noscript.{0,50}javascript",  # noscript warnings
        # Loading/placeholder states
        r"loading.{0,10}\.\.\.",  # Loading text
        r"(please|kindly)\s*wait",  # Wait messages
        r"initializing.{0,30}(application|app)",  # Init messages
    ]


# =============================================================================
# REGISTRY & UTILITY FUNCTIONS
# =============================================================================


SCHEMA_REGISTRY = {
    "recipe": Recipe,
    "event": Event,
    "pricing_table": PricingTable,
    "job_posting": JobPosting,
    "person": Person,
    "error_page": ErrorPage,
    "auth_required": AuthRequired,
    "empty_shell": EmptySPAShell,
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


# Manual annotation templates for each fragment type
ANNOTATION_TEMPLATES = {
    "recipe": {
        "type": "recipe",
        "name": "TODO",
        "description": "TODO",
        "author": "TODO",
        "prep_time": "TODO",
        "cook_time": "TODO",
        "total_time": "TODO",
        "servings": "TODO",
        "ingredients": ["TODO"],
        "instructions": ["TODO"],
        "rating": {"score": "TODO", "review_count": "TODO"},
    },
    "event": {
        "type": "event",
        "title": "TODO",
        "datetime": "TODO",
        "location": "TODO",
        "venue_name": "TODO",
        "price": "TODO",
        "organizer": "TODO",
        "attendee_count": "TODO",
        "description": "TODO",
        "event_type": "TODO",
    },
    "pricing_table": {
        "type": "pricing_table",
        "plans": [
            {
                "name": "TODO",
                "price": "TODO",
                "price_amount": "TODO",
                "currency": "TODO",
                "billing_period": "TODO",
                "features": ["TODO"],
                "description": "TODO",
            }
        ],
    },
    "job_posting": {
        "type": "job_posting",
        "title": "TODO",
        "company": "TODO",
        "location": "TODO",
        "department": "TODO",
        "posted_date": "TODO",
        "employment_type": "TODO",
        "description": "TODO",
    },
    "person": {
        "type": "person",
        "name": "TODO",
        "title": "TODO",
        "bio": "TODO",
        "email": "TODO",
        "phone": "TODO",
        "linkedin": "TODO",
        "image_url": "TODO",
    },
    "auth_required": {
        "type": "auth_required",
        "message": "TODO: Extract the main authentication message",
    },
    "error_page": {
        "type": "error_page",
        "error_code": "TODO: Extract error code (e.g., 404, 500)",
        "message": "TODO: Extract error message",
        "description": "TODO: Extract error description",
    },
    "empty_spa_shell": {
        "type": "empty_spa_shell",
        "message": "TODO: Describe why content is unavailable (e.g., requires JavaScript)",
    },
    "captcha_or_bot_check": {
        "type": "captcha_or_bot_check",
        "message": "TODO: Extract captcha/bot check message",
    },
    "paywall_content": {
        "type": "paywall_content",
        "message": "TODO: Extract paywall message",
    },
    "negative": {
        "type": "negative",
        "message": "TODO: Describe why this is a negative example",
    },
}


def generate_annotation_template(fragment_type: str) -> dict:
    """Get annotation template for a fragment type."""
    if fragment_type not in ANNOTATION_TEMPLATES:
        return {"type": fragment_type, "TODO": "Define template"}
    return ANNOTATION_TEMPLATES[fragment_type].copy()
