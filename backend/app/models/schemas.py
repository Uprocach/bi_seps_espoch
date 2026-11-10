from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

# Primitivos
PeriodStr = str
RucStr = str
SegmentCode = Literal[
    "SEGMENTO_1",
    "SEGMENTO_1_MUTUALISTA",
    "SEGMENTO_2",
    "SEGMENTO_3",
    "SEGMENTO_4",
    "SEGMENTO_5"
]
AggregationLevel = Literal["country", "segment", "entity"]
Frequency = Literal["monthly", "quarterly"]
Polarity = Literal["higher_is_better", "lower_is_better", "neutral"]

# Metadata
class Segment(BaseModel):
    code: SegmentCode
    label: str
    reporting_frequency: Frequency
    entity_count: int

class Province(BaseModel):
    code: str
    name: str
    entity_count: int | None = None

class PeriodCatalog(BaseModel):
    frequency: Frequency
    min: PeriodStr
    max: PeriodStr
    latest: PeriodStr
    available: list[PeriodStr]

class IndicatorMeta(BaseModel):
    id: str
    name: str
    short_name: str
    category: str
    unit: str
    decimals: int
    polarity: Polarity
    seps_ficha_number: int | None = None
    latest_value: float | None = None
    methodological_note: str | None = None

class FiltersMetadata(BaseModel):
    segments: list[Segment]
    provinces: list[Province]
    periods: PeriodCatalog
    indicators: list[IndicatorMeta]
    data_as_of: str

# Entities
class EntitySummary(BaseModel):
    ruc: RucStr
    razon_social: str
    entity_type: Literal["COOPERATIVA", "MUTUALISTA", "CAJA_CENTRAL"]
    segment: SegmentCode
    province: Province | None = None
    total_assets_usd: float | None = None
    first_period: PeriodStr
    last_period: PeriodStr
    is_active: bool

class Pagination(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int

class EntityListResponse(BaseModel):
    data: list[EntitySummary]
    pagination: Pagination

# Indicators Series
class SeriesPoint(BaseModel):
    period: PeriodStr
    value: float | None = None
    numerator: float | None = None
    denominator: float | None = None
    entity_count: int = 1

class Series(BaseModel):
    key: str
    label: str
    level: AggregationLevel
    segment: SegmentCode | None = None
    points: list[SeriesPoint]

class PeriodRange(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: PeriodStr = Field(alias="from")
    to: PeriodStr

class FiltersApplied(BaseModel):
    segment: list[SegmentCode] = []
    province: list[str] = []
    ruc: list[RucStr] = []

class IndicatorSeriesResponse(BaseModel):
    indicator: IndicatorMeta
    level: AggregationLevel
    frequency: Frequency
    period_range: PeriodRange
    filters_applied: FiltersApplied
    series: list[Series]
    generated_at: str

# -------------------------------------------------------------
# Modelos Capa Pro: Autenticación, RBAC y Auditoría
# -------------------------------------------------------------
RoleEnum = Literal["investigador", "auditor", "administrador"]

class LoginRequest(BaseModel):
    username: str | None = Field(default=None, description="Usuario institucional ESPOCH")
    user: str | None = Field(default=None, description="Alias para usuario")
    password: str = Field(..., min_length=4, description="Contraseña de acceso")
    role: str = Field(default="investigador", description="Rol solicitado (investigador, auditor, administrador)")

class UserResponse(BaseModel):
    sub: str
    role: RoleEnum
    name: str
    email: str
    permissions: list[str] = []
    authenticated: bool = True
    must_change_password: bool = False

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=4, description="Contraseña actual")
    new_password: str = Field(..., min_length=6, description="Nueva contraseña elegida")

class AdminUserListItem(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: RoleEnum
    is_active: bool
    must_change_password: bool
    created_at: str
    last_login_at: str | None = None

class AdminUsersListResponse(BaseModel):
    users: list[AdminUserListItem]
    total: int

class AdminUserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., min_length=5, max_length=150)
    full_name: str = Field(..., min_length=3, max_length=150)
    role: RoleEnum = "investigador"
    initial_password: str | None = None

class AdminUserResetPasswordResponse(BaseModel):
    user_id: int
    username: str
    temp_password: str
    message: str

class BulkImportUserItem(BaseModel):
    username: str | None = None
    email: str | None = None
    full_name: str
    role: RoleEnum = "investigador"
    password: str | None = None

class BulkImportRequest(BaseModel):
    users: list[BulkImportUserItem]

class BulkImportResponse(BaseModel):
    imported_count: int
    skipped_count: int
    created_users: list[dict]
    errors: list[str] = []

class AuditEventCreate(BaseModel):
    user_sub: str
    user_role: str
    action: str
    resource: str
    details: dict = {}
    ip_address: str | None = None
    user_agent: str | None = None

# -------------------------------------------------------------
# Modelos Capa Pro: Semáforo Regulatorio CAMEL
# -------------------------------------------------------------
CamelDimension = Literal[
    "capital",
    "calidad_de_activos",
    "manejo_administrativo",
    "rentabilidad",
    "liquidez"
]

TrafficLightStatus = Literal["GREEN", "YELLOW", "RED"]

class CamelEvaluation(BaseModel):
    status: TrafficLightStatus
    value: float | None
    normative_reference: str | None = None
    message: str
    polarity: Polarity = "higher_is_better"
    threshold: dict = {}

# -------------------------------------------------------------
# Modelos Capa Pro: Benchmarking Multi-Entidad
# -------------------------------------------------------------
class BenchmarkingCompareRequest(BaseModel):
    entity_ids: list[str] = Field(..., min_length=1, max_length=5, description="Lista de hasta 5 RUCs de cooperativas a comparar")
    start_date: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Periodo inicial YYYY-MM")
    end_date: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Periodo final YYYY-MM")
    camel_dimension: CamelDimension | None = Field(default=None, description="Dimensión CAMEL opcional")

    @field_validator("entity_ids")
    @classmethod
    def validate_entities_count(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Debe seleccionar al menos una entidad para benchmarking.")
        if len(v) > 5:
            raise ValueError("El benchmarking permite contrastar un máximo de 5 cooperativas simultáneamente.")
        # Limpiar duplicados preservando orden
        seen = set()
        unique = []
        for ruc in v:
            clean = ruc.strip()
            if clean and clean not in seen:
                seen.add(clean)
                unique.append(clean)
        return unique

class BenchmarkingIndicatorRow(BaseModel):
    indicator_id: str
    indicator_name: str
    dimension: str
    unit: str
    polarity: Polarity
    seps_ficha_number: int | None = None
    entity_values: dict[str, float | None]
    entity_evaluations: dict[str, CamelEvaluation]
    segment1_baseline: float | None = None
    country_baseline: float | None = None

class BenchmarkingSeriesPoint(BaseModel):
    period: str
    entity_values: dict[str, float | None]
    segment1_baseline: float | None = None
    country_baseline: float | None = None

class BenchmarkingCompareResponse(BaseModel):
    entities: list[EntitySummary]
    start_date: str
    end_date: str
    camel_dimension: str | None = None
    indicators: list[BenchmarkingIndicatorRow]
    time_series: dict[str, list[BenchmarkingSeriesPoint]] = {}
    total_indicators: int
    generated_at: str

# -------------------------------------------------------------
# Modelos Capa Pro: Exportación
# -------------------------------------------------------------
class ExportRequest(BaseModel):
    entity_ids: list[str] = Field(..., min_length=1, max_length=5)
    start_date: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    end_date: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    camel_dimension: CamelDimension | None = None

# -------------------------------------------------------------
# Modelos Capa Pro: Ranking de COACs por Ficha
# -------------------------------------------------------------
class EntityRankingItem(BaseModel):
    rank: int
    national_rank: int | None = None
    ruc: str
    razon_social: str
    segment: str
    province: str | None = None
    total_assets_usd: float | None = None
    value: float
    camel_evaluation: CamelEvaluation
    diff_country: float | None = None
    diff_segment1: float | None = None

class BenchmarkingRankingResponse(BaseModel):
    indicator: IndicatorMeta
    period: str
    segment_filter: str | None = None
    province_filter: str | None = None
    selected_rucs: list[str] | None = None
    segment1_baseline: float | None = None
    country_baseline: float | None = None
    ranking: list[EntityRankingItem]
    total_ranked: int
    generated_at: str
