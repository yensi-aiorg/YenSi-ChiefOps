"""
Dashboard and widget models for the ChiefOps visualization layer.

Dashboards are composed of dynamic widgets created through natural language
conversation or as system defaults. Widgets define what data to fetch
(DataQuery) and how to render it (display_config / widget_type).
"""

from enum import Enum

from pydantic import BaseModel, Field

from app.models.base import MongoBaseModel, generate_uuid

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DashboardType(str, Enum):
    """Type of dashboard."""

    MAIN = "main"
    PROJECT_STATIC = "project_static"
    PROJECT_CUSTOM = "project_custom"


class WidgetType(str, Enum):
    """Supported visualization types for dashboard widgets."""

    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    GANTT_CHART = "gantt_chart"
    DATA_TABLE = "data_table"
    KPI_CARD = "kpi_card"
    SUMMARY_TEXT = "summary_text"
    PERSON_GRID = "person_grid"
    TIMELINE = "timeline"
    ACTIVITY_FEED = "activity_feed"


class QueryType(str, Enum):
    """Type of data aggregation query a widget can perform."""

    COUNT = "count"
    GROUP_COUNT = "group_count"
    TIME_SERIES = "time_series"
    TOP_N = "top_n"
    AGGREGATE = "aggregate"


# ---------------------------------------------------------------------------
# Embedded sub-documents
# ---------------------------------------------------------------------------


class WidgetPosition(BaseModel):
    """Grid position and dimensions for a widget on a dashboard."""

    row: int = Field(
        default=0,
        ge=0,
        description="Grid row index (0-based).",
    )
    col: int = Field(
        default=0,
        ge=0,
        description="Grid column index (0-based).",
    )
    width: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Width in grid columns (1-12).",
    )
    height: int = Field(
        default=4,
        ge=1,
        le=8,
        description="Height in grid rows (1-8).",
    )


class DataQuery(BaseModel):
    """
    Defines what data to fetch and how to aggregate it for a widget.
    This is the abstract query specification -- the backend resolves it
    into actual MongoDB aggregation pipelines at render time.
    """

    collection: str = Field(
        ...,
        description="MongoDB collection to query (e.g. 'tasks', 'people', 'messages').",
    )
    query_type: QueryType = Field(
        default=QueryType.COUNT,
        description="Type of aggregation to perform.",
    )
    match_filters: dict = Field(
        default_factory=dict,
        description="MongoDB match-stage filters as key-value pairs.",
    )
    group_by: str | None = Field(
        default=None,
        description="Field to group results by.",
    )
    sort_by: str | None = Field(
        default=None,
        description="Field to sort results by.",
    )
    sort_order: str = Field(
        default="desc",
        description="Sort direction ('asc' or 'desc').",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of results to return.",
    )
    date_field: str | None = Field(
        default=None,
        description="Field name to use for time-based queries.",
    )
    date_bucket: str | None = Field(
        default=None,
        description="Time bucket size for time-series queries (e.g. 'day', 'week', 'month').",
    )
    aggregation: dict | None = Field(
        default=None,
        description="Custom aggregation pipeline stages (for advanced queries).",
    )


# ---------------------------------------------------------------------------
# Primary model: Dashboard
# ---------------------------------------------------------------------------


class Dashboard(MongoBaseModel):
    """
    A dashboard composed of widgets. There are three dashboard types:

    - **main**: The global overview dashboard visible on the home screen.
    - **project_static**: System-generated dashboard for a specific project.
    - **project_custom**: COO-customized dashboard for a specific project.

    MongoDB collection: ``dashboards``
    """

    dashboard_id: str = Field(
        default_factory=generate_uuid,
        description="Unique dashboard identifier (UUID v4).",
    )
    project_id: str | None = Field(
        default=None,
        description="Linked project (None for the main dashboard).",
    )
    dashboard_type: DashboardType = Field(
        default=DashboardType.MAIN,
        description="Type of dashboard.",
    )
    name: str = Field(
        default="Dashboard",
        min_length=1,
        max_length=200,
        description="Display name of the dashboard.",
    )
    widget_ids: list[str] = Field(
        default_factory=list,
        description="Ordered list of widget_id values rendered on this dashboard.",
    )
    layout: dict = Field(
        default_factory=dict,
        description="Dashboard-level layout configuration (grid settings, breakpoints, etc.).",
    )


# ---------------------------------------------------------------------------
# Primary model: WidgetSpec
# ---------------------------------------------------------------------------


class WidgetSpec(MongoBaseModel):
    """
    Specification for a dynamic widget on a dashboard.

    Widgets are created either by the COO through natural language
    (e.g. 'Show me a bar chart of tasks per person') or as system
    defaults during project initialization. The data_query field
    defines WHAT data to show. The display_config field contains
    rendering hints (colors, labels, chart options).

    MongoDB collection: ``dashboard_widgets``
    """

    widget_id: str = Field(
        default_factory=generate_uuid,
        description="Unique widget identifier (UUID v4).",
    )
    dashboard_id: str = Field(
        ...,
        description="Dashboard this widget belongs to (format: '{project_id}_custom' or 'main').",
    )
    widget_type: WidgetType = Field(
        ...,
        description="Visualization type.",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Display title of the widget.",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Optional description of what this widget shows.",
    )

    position: WidgetPosition = Field(
        default_factory=WidgetPosition,
        description="Grid position and dimensions on the dashboard.",
    )
    data_query: DataQuery = Field(
        ...,
        description="Data query specification defining what data to fetch.",
    )
    display_config: dict = Field(
        default_factory=dict,
        description="Rendering configuration (colors, labels, chart options, ECharts spec, etc.).",
    )
