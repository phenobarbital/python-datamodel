# test_dashboard_widget.py
from typing import Dict, Optional, Union
from uuid import UUID
from datetime import datetime
from slugify import slugify
import pytest
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError  # or from datamodel.exceptions import ValidationError


class Dashboard(BaseModel):

    dashboard_id: UUID = Field(
        required=False, primary_key=True, db_default="auto", repr=False
    )
    name: str = Field(required=True)
    description: str
    params: Optional[dict] = Field(required=False, db_type="jsonb")
    enabled: bool = Field(required=True, default=False)
    shared: bool = Field(required=True, default=False)
    published: bool = Field(required=True, default=False)
    allow_filtering: bool = Field(required=True, default=False)
    allow_widgets: bool = Field(required=True, default=False)
    attributes: Optional[dict] = Field(required=False, db_type="jsonb")
    dashboard_type: str
    slug: str
    position: int = Field(required=True, default=1)
    cond_definition: Optional[dict] = Field(required=False, db_type="jsonb")
    # Optional[Dict[str, Union[int, Dict[str, int]]]]
    widget_location: Optional[Dict[str, Union[int, Dict[str, int]]]] = Field(
        required=False, db_type="jsonb"
    )
    module_id: int = Field(required=False)
    program_id: int = Field(required=False)
    user_id: int = Field(required=False)
    render_partials: bool = Field(required=True, default=False)
    conditions: Optional[dict] = Field(required=False, db_type="jsonb")
    save_filtering: bool = Field(required=True, default=False)
    filtering_show: Optional[dict] = Field(required=False, db_type="jsonb")
    is_system: bool = Field(required=True, default=False)
    created_by: int = Field(required=False)
    signed_ts: Optional[datetime] = Field(required=False)

    def __getitem__(self, item):
        return getattr(self, item)

    def __post_init__(self) -> None:
        if not self.slug:
            slug = slugify(self.name, separator="_")
            self.slug = f"{slug}"
        super(Dashboard, self).__post_init__()

    class Meta:
        driver = "pg"
        name = "dashboards"
        strict = True


class Widget(BaseModel):

    widget_id: UUID = Field(
        required=False,
        primary_key=True,
        db_default="auto",
        repr=False
    )
    widget_name: str = Field(required=False)
    title: str = Field(required=False)
    description: str
    url: str = Field(required=False)
    params: Optional[dict] = Field(required=False, db_type="jsonb")
    embed: str = Field(required=False)
    attributes: Optional[dict] = Field(required=False, db_type="jsonb")
    conditions: Optional[dict] = Field(required=False, db_type="jsonb")
    cond_definition: Optional[dict] = Field(required=False, db_type="jsonb")
    where_definition: Optional[dict] = Field(required=False, db_type="jsonb")
    format_definition: Optional[dict] = Field(required=False, db_type="jsonb")
    query_slug: Optional[dict] = Field(required=False, db_type="jsonb")
    save_filtering: bool = Field(required=True, default=False)
    master_filtering: bool = Field(required=True, default=True)
    module_id: int = Field(required=False)
    program_id: int = Field(required=True)
    dashboard_id: UUID = Field(required=True)
    template_id: UUID = Field(required=False, default=None)
    widget_slug: str = Field(required=False)
    widgetcat_id: int = Field(required=False)
    allow_filtering: bool = Field(required=False, default=True)
    filtering_show: Optional[dict] = Field(required=False, db_type="jsonb")
    widget_type_id: str = Field(required=False)
    user_id: int = Field(required=False, default=None)
    active: bool = Field(required=True, default=True)
    published: bool = Field(required=True, default=True)
    inserted_at: datetime = Field(required=False)
    inserted_by: int = Field(required=False)
    updated_at: datetime = Field(required=False)
    updated_by: int = Field(required=False)

    def __getitem__(self, item):
        return getattr(self, item)

    def __post_init__(self) -> None:
        if not self.widget_slug:
            name = self.widget_name or self.title
            try:
                slug = slugify(name, separator="_")
                self.widget_slug = f"{slug}"
            except TypeError:
                self.widget_slug = None
        super(Widget, self).__post_init__()

    class Meta:
        driver = "pg"
        name = "widgets"
        strict = True

def test_dashboard_basic():
    """
    Test that we can create a Dashboard with minimal fields, plus verifying
    automatically generated fields like slug.
    """
    # Provide the minimal or typical fields
    dash = Dashboard(
        name="My Dashboard",
        dashboard_type="general",
        description="Testing dashboard creation"
    )
    assert dash.name == "My Dashboard"
    assert dash.slug == "my_dashboard"  # Because of your slugify logic

    # Since strict=True, check that extra unknown fields are not accepted
    with pytest.raises(TypeError):
        # Passing an unknown field "foo" should break in strict mode
        Dashboard(
            name="Bad Dashboard",
            dashboard_type="something",
            foo="bar"
        )

def test_dashboard_payload():
    """
    Test that passing in a more complete payload with widget_location,
    attributes, etc. handles them properly.
    """
    payload = {
        "dashboard_id": "a7c1e1e4-7b6f-4c1e-8b3c-6b0f1b7d5f3a",
        "signed_ts": "2021-09-01 12:22",
        "attributes": {
            "cols": "12",
            "icon": "fa fa-th",
            "color": "#51981e",
            "width": "720",
            "height": "480",
            "user_id": 15779,
            "explorer": "v3",
            "fg_color": "#333333",
            "row_header": "false",
            "multiselect": "true",
            "widget_location": {
                "timestamp": 1734121193554,
                "Mso Promotions": {
                    "h": 44,
                    "w": 12,
                    "x": 0,
                    "y": 0
                }
            }
        },
        "widget_location": {
            "timestamp": 1735573243363,
            "Retail360 Flow #ZLJAH": {
                "h": 21,
                "w": 5,
                "x": 5,
                "y": 10
            },
            "Retail360 Chart1 #YOYHK": {
                "h": 31,
                "w": 5,
                "x": 0,
                "y": 0
            },
            "Retail360 Chart2 #HZRDQ": {
                "h": 32,
                "w": 5,
                "x": 0,
                "y": 31
            },
            "Retail360 Chart3 #FXWRA": {
                "h": 31,
                "w": 5,
                "x": 5,
                "y": 63
            },
            "Retail360 Chart4 #RPMPC": {
                "h": 31,
                "w": 5,
                "x": 0,
                "y": 63
            },
            "Retail360 Quickfacts #ZLJGE": {
                "h": 32,
                "w": 5,
                "x": 5,
                "y": 31
            },
            "Retail360 National Sales Ranks #JTHHI": {
                "h": 10,
                "w": 5,
                "x": 5,
                "y": 0
            }
        }
    }
    dash = Dashboard(
        name="Dashboard 1",
        description="Full payload test",
        dashboard_type="dashboard",
        **payload
    )
    # Check fields were parsed
    assert dash.dashboard_id == UUID("a7c1e1e4-7b6f-4c1e-8b3c-6b0f1b7d5f3a")
    assert dash.signed_ts == datetime(2021, 9, 1, 12, 22)
    assert dash.attributes["icon"] == "fa fa-th"
    # `widget_location` is a dict, with nested dict as well:
    assert "Retail360 Flow #ZLJAH" in dash.widget_location
    assert dash.widget_location["timestamp"] == 1735573243363
    assert dash.widget_location["Retail360 Flow #ZLJAH"]["h"] == 21

def test_widget_basic():
    """
    Test creating a Widget with minimal required fields.
    """
    # The code below is the minimal set you identified as required
    widget = Widget(
        widget_name="Widget 1",
        description="This is a widget",
        dashboard_id="a7c1e1e4-7b6f-4c1e-8b3c-6b0f1b7d5f3a",
        program_id=1,
        user_id=1,
    )
    assert widget.widget_name == "Widget 1"
    # Because you auto-generate widget_slug if not provided:
    assert widget.widget_slug == "widget_1"
    assert widget.dashboard_id == UUID("a7c1e1e4-7b6f-4c1e-8b3c-6b0f1b7d5f3a")
    assert widget.program_id == 1
    assert widget.user_id == 1

def test_widget_strict_extra():
    """
    Ensures that unknown fields in 'strict' mode raise an error.
    """
    with pytest.raises(TypeError):
        Widget(
            widget_name="Widget Extra",
            description="Invalid extra field test",
            dashboard_id="a7c1e1e4-7b6f-4c1e-8b3c-6b0f1b7d5f3a",
            program_id=1,
            user_id=1,
            invalid_field="Oops"  # this should cause a failure in strict mode
        )

def test_widget_validation_error():
    """
    Example of how to catch ValidationError if any required fields are missing
    or invalid.
    """
    # Suppose 'dashboard_id' and 'program_id' are truly required by the model.
    # If we omit them, we should get a ValidationError.
    with pytest.raises(ValueError):
        Widget(
            widget_name="Missing fields",
            description="No dash or program",
            user_id=1,
        )
