from uuid import UUID, uuid4
from enum import Enum
from typing import List, Dict, Any, Optional, Union
import contextlib
from ..base import BaseModel, Field, register_renderer

# https://adaptivecards.io/explorer/Media.html

def auto_uuid(*args, **kwargs):  # pylint: disable=W0613
    return uuid4()

class ContainerStyle(str, Enum):
    """Shared Style for all containers in a Adaptive Card."""
    default = 'default'
    accent = 'accent'
    good = 'good'
    attention = 'attention'
    warning = 'warning'
    emphasis = 'emphasis'

class ContainerColor(str, Enum):
    """Shared Color for all containers in a Adaptive Card."""
    default = 'default'
    dark = 'dark'
    light = 'light'
    accent = 'accent'
    good = 'good'
    attention = 'attention'
    warning = 'warning'


class FontType(str, Enum):
    """Font Type for TextBlock."""
    default = 'default'
    monospace = 'monospace'

class FontSize(str, Enum):
    """Font Size for TextBlock."""
    default = 'default'
    small = 'small'
    medium = 'medium'
    large = 'large'
    extraLarge = 'extraLarge'

class FontWeight(str, Enum):
    """Font Weight for TextBlock."""
    default = 'default'
    lighter = 'lighter'
    bolder = 'bolder'


class SelectAction(str, Enum):
    """Action to be taken when a cell is selected."""
    exectute = 'Action.Execute'
    submit = 'Action.Submit'
    openUrl = 'Action.OpenUrl'
    toggleVisibility = 'Action.ToggleVisibility'


class CardElement(BaseModel):
    """Base class for Adaptive card elements."""
    type: str

    class Meta:
        as_objects: True
        remove_nulls = True

    def __post_init__(self):
        if not self.type:
            self.type = self.__class__.__name__
        return super().__post_init__()

    def to_adaptive(self) -> Dict[str, Any]:
        """Convert to AdaptiveCard JSON-representation."""
        return self.to_dict()

class TextBlock(CardElement):
    text: str
    size: Optional[str] = None
    weight: Optional[str] = None
    horizontalAlignment: Optional[str] = None
    wrap: Optional[bool] = Field(default=True)
    style: Optional[str] = None
    isSubtle: Optional[bool] = None


class TextRun(CardElement):
    """Defines a single run of formatted text."""
    type: str = Field(default='TextRun')
    text: str
    color: Optional[ContainerStyle] = Field(ContainerStyle.default)
    fontType: Optional[FontType] = Field(FontType.default)
    highlight: bool = Field(default=False)
    isSubtle: bool = Field(default=False)
    italic: bool = Field(default=False)
    strikethrough: bool = Field(default=False)
    underline: bool = Field(default=False)
    selectAction: Optional[SelectAction] = Field(default=None)
    size: Optional[FontSize] = Field(default=None)
    weight: Optional[FontWeight] = Field(default=FontWeight.default)


class RichTextBlock(CardElement):
    type: str = Field(default='RichTextBlock')
    inlines: List[Union[str, TextRun]] = Field(default_factory=list)
    horizontalAlignment: Optional[str] = Field(default='left')


class Column(CardElement):
    items: Optional[List[CardElement]] = Field(default_factory=list)
    width: Optional[str] = Field(default='auto')

    def add_item(self, item: Union[CardElement, List[CardElement]]):
        if isinstance(item, list):
            self.items.extend(item)
        else:
            self.items.append(item)

    def to_adaptive(self) -> Dict[str, Any]:
        """Ensure proper JSON serialization."""
        return {
            "type": "Column",
            "items": [
                item.to_adaptive() for item in self.items if isinstance(item, CardElement)  # noqa
            ],  # Prevent duplicates
            "width": self.width
        }


class InputElement(CardElement):
    """Base class for input elements."""
    type: str = Field(default='Input.Text')
    id: str
    label: Optional[str] = None
    placeholder: Optional[str] = None

class InputText(InputElement):
    style: Optional[str] = None
    isRequired: Optional[bool] = None
    errorMessage: Optional[str] = None
    isMultiline: Optional[bool] = None

class InputNumber(InputElement):
    min: Optional[int] = None
    max: Optional[int] = None
    value: Optional[int] = None
    errorMessage: Optional[str] = None

class InputDate(InputElement):
    value: Optional[str] = None

class InputTime(InputElement):
    value: Optional[str] = None

class Choice(BaseModel):
    title: str
    value: str

class InputChoiceSet(InputElement):
    choices: List[Choice]
    value: Optional[str] = None
    isMultiSelect: Optional[bool] = None
    style: Optional[str] = None

class InputToggle(InputElement):
    title: str
    valueOn: str
    valueOff: str
    isRequired: Optional[bool] = None
    errorMessage: Optional[str] = None

class FactElement(BaseModel):
    """A single fact."""
    title: str
    value: str

class Image(CardElement):
    type: str = Field(default='Image')
    url: str
    size: Optional[str] = None
    style: Optional[str] = None
    altText: Optional[str] = None


class MediaSource(CardElement):
    mimeType: str
    url: str

class CaptionSource(CardElement):
    mimeType: str = Field(default='vtt')
    label: str = Field(default='English')
    url: str

class Media(CardElement):
    type: str = Field(default='Media')
    sources: List[MediaSource] = Field(default_factory=list)
    poster: Optional[str] = None
    captionSources: List[CaptionSource] = Field(default_factory=list)

    def add_source(self, source: Union[str, MediaSource]):
        if isinstance(source, str):
            source = MediaSource(url=source, mimeType='video/mp4')
        self.sources.append(source)
        return self

class ImageFillMode(str, Enum):
    """Describes how the image should be filled."""
    cover = 'cover'
    repeatHorizontally = 'repeatHorizontally'
    repeatVertically = 'repeatVertically'
    repeat = 'repeat'

class BackgroundImage(CardElement):
    type: str = Field(default='BackgroundImage')
    url: str
    fillMode: Optional[ImageFillMode] = Field(default=ImageFillMode.cover)

## Table structure:

class TableCell(BaseModel):
    """A single cell in a TableRow."""
    type: str = Field(default='TableCell')
    style: Optional[ContainerStyle] = Field(default=ContainerStyle.default)
    selectAction: Optional[SelectAction] = Field(default=None)
    items: List[CardElement] = Field(default_factory=list)
    backgroundImage: Union[BackgroundImage, str] = Field(default=None)

    def to_adaptive(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "items": [item.to_adaptive() for item in self.items]
        }


class TableRow(BaseModel):
    """A row in a Table."""
    type: str = Field(default='TableRow')
    cells: List[TableCell] = Field(default_factory=list)

    def add_cell(self, cell: TableCell):
        self.cells.append(cell)

    def new_cell(self, block: Union[CardElement, List[CardElement]]):
        if isinstance(block, CardElement):
            block = [block]
        cell = TableCell(items=block)
        self.cells.append(cell)

    def to_adaptive(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "cells": [cell.to_adaptive() for cell in self.cells]
        }

## Containers:
class FactSet(CardElement):
    """A set of facts."""
    type: str = Field(default='FactSet')
    facts: List[FactElement] = Field(default_factory=list)

    def to_adaptive(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "facts": [fact.to_dict() for fact in self.facts]
        }

class ColumnSet(CardElement):
    """A set of columns."""
    type: str = Field(default='ColumnSet')
    columns: List[Column] = Field(default_factory=list)

    def add_column(self, column: Union[Column, List[Column]]):
        if isinstance(column, Column):
            column = [column]
        self.columns.extend(column)
        # return the collection added of columns
        return column

    def create_column(self, content: CardElement):
        """Create a new column with a single item."""
        column = Column()
        column.add_item(content)
        self.columns.append(column)
        return column

    def to_adaptive(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "columns": [column.to_adaptive() for column in self.columns]
        }

class CardSection(CardElement):
    type: str = Field(default='Container')
    items: List[CardElement] = Field(default_factory=list)
    facts: list[FactSet] = Field(default_factory=list)

    def addFacts(self, facts: Union[FactSet, List[FactSet]]):
        if isinstance(facts, FactSet):
            facts = [facts]
        self.facts.extend(facts)

    def addItem(self, item: CardElement):
        self.items.append(item)

    def to_adaptive(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "items": [item.to_adaptive() for item in self.items]
        }

class ColumnDefinition(BaseModel):
    """A column definition in a Table."""
    width: str = Field(default='auto')

    def to_adaptive(self) -> Dict[str, Any]:
        return {
            "width": self.width
        }

class Table(CardElement):
    """A table layout containing multiple rows."""
    type: str = Field(default='Table')
    columns: List[ColumnDefinition] = Field(default_factory=list)
    rows: List[TableRow] = Field(default_factory=list)
    firstRowAsHeader: bool = Field(default=True)
    showGridLines: bool = Field(default=True)
    gridStyle: Optional[ContainerStyle] = Field(default=ContainerStyle.default)

    def add_row(self, row: TableRow):
        self.rows.append(row)

    def new_row(self, cells: Union[TableCell, List[TableCell]]):
        if isinstance(cells, TableCell):
            cells = [cells]
        row = TableRow(cells=cells)
        self.rows.append(row)
        return row

    def to_adaptive(self) -> Dict[str, Any]:
        # Ensure columns are generated based on the number of cells in the first row
        num_columns = max(len(row.cells) for row in self.rows) if self.rows else 0
        self.columns = [ColumnDefinition() for _ in range(num_columns)]

        return {
            "type": self.type,
            "gridStyle": self.gridStyle,
            "firstRowAsHeader": self.firstRowAsHeader,
            "showGridLines": self.showGridLines,
            "columns": [column.to_adaptive() for column in self.columns],
            "rows": [row.to_adaptive() for row in self.rows]
        }

# Define a Enum for Image Sizes:
class ImageSize(str, Enum):
    auto = 'auto'
    stretch = 'stretch'
    small = 'small'
    medium = 'medium'
    large = 'large'


class ImageSet(CardElement):
    """A set of images displayed together."""
    type: str = Field(default='ImageSet')
    images: List['Image'] = Field(default_factory=list)
    imageSize: Optional[ImageSize] = Field(default=ImageSize.auto)

    def add_image(self, image: Union[Image, List[Image]]):
        if isinstance(image, Image):
            image = [image]
        self.images.extend(image)

    def new_image(self, images: Union[str, Image, tuple]):
        if isinstance(images, str):
            img = Image(
                url=images,
                altText=images
            )
        elif isinstance(images, tuple):
            img = Image(
                url=images[0],
                altText=images[1]
            )
        else:
            img = images
        self.images.append(img)

    def to_adaptive(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "images": [image.to_adaptive() for image in self.images],
            "imageSize": self.imageSize
        }


class CardAction(BaseModel):
    """Base class for Adaptive card actions."""
    type: str
    title: str
    data: Optional[Dict[str, Any]] = Field(default=None)
    card: Optional['AdaptiveCard'] = Field(default=None)

    class Meta:
        as_objects: True
        remove_nulls = True

    def __post_init__(self):
        if not self.type:
            self.type = f"Action.{self.__class__.__name__}"
        return super().__post_init__()

    def to_adaptive(self) -> Dict[str, Any]:
        """Convert to AdaptiveCard JSON-representation."""
        return self.to_dict()

### Main Class: AdaptiveCard
class AdaptiveCard(BaseModel):
    card_id: UUID = Field(required=False, default=auto_uuid, repr=False)
    content_type: str = Field(
        default="application/vnd.microsoft.card.adaptive",
        repr=False
    )
    schema: str = "http://adaptivecards.io/schemas/adaptive-card.json"
    card_type: str = "AdaptiveCard"
    title: str
    summary: str
    minHeight: Optional[str] = None
    body: List[CardElement] = Field(default_factory=list)
    backgroundImage: Optional[BackgroundImage] = Field(default=None)
    body_objects: List[Dict[str, Any]] = Field(default_factory=list, repr=False)
    actions: List[CardAction] = Field(default_factory=list)
    sections: List[CardSection] = Field(default_factory=list)
    version: str = Field(default="1.5")

    def __post_init__(self):
        if self.version == "1.6":  # Forcing Version to MS Teams
            self.version = "1.5"
        return super().__post_init__()

    def add_text(self, text: str, **kwargs):
        self.body.append(
            TextBlock(type="TextBlock", text=text, **kwargs)
        )

    def add_body_element(self, element: CardElement):
        self.body.append(element)
        return element

    def add_background(self, background: Union[str, BackgroundImage]):
        """Adding a Background Image to the Card."""
        if isinstance(background, str):
            background = BackgroundImage(url=background)
        self.backgroundImage = background
        return background

    def add_action(self, action: CardAction):
        self.actions.append(action)

    def add_section(self, **kwargs):
        section = CardSection(**kwargs)
        self.sections.append(section)
        return section

    def add_input(
        self,
        id: str,
        label: str,
        is_required: bool = False,
        error_message: str = None,
        input_type: str = 'Text',
        style: str = None
    ):
        element = {
            "type": f"Input.{input_type}",
            "id": id,
            "label": label,
            "isRequired": is_required
        }
        if error_message is not None:
            element["errorMessage"] = error_message
        if style is not None:
            element["style"] = style
        if element:
            self.body_objects.append(
                element
            )

    def to_dict(self) -> dict:
        data = super().to_dict(remove_nulls=True)
        del data['card_id']
        del data['body_objects']
        del data['actions']
        del data['content_type']
        del data['version']
        data['type'] = data.pop('card_type')
        data['@type'] = "MessageCard"
        data['@context'] = "http://schema.org/extensions"
        return data

    def to_adaptive(self) -> Dict[str, Any]:
        """Convert to AdaptiveCard JSON-representation."""
        # Build Body based on content:
        body = []
        properties = {}
        if self.backgroundImage:
            properties["backgroundImage"] = self.backgroundImage.to_dict()
        if self.minHeight:
            properties["minHeight"] = self.minHeight
        if self.title:
            body.append({
                "type": "TextBlock",
                "size": "Medium",
                "weight": "Bolder",
                "text": self.title,
                "horizontalAlignment": "Center",
                "wrap": True,
                "style": "heading"
            })
        if self.summary:
            body.append({
                "type": "TextBlock",
                "size": "large",
                "weight": "bolder",
                "text": self.summary
            })
        if self.body:
            body.extend(element.to_adaptive() for element in self.body)
        if self.sections:
            body.extend(
                {
                    "type": "Container",
                    "items": [section.to_adaptive() for section in self.sections]
                }
            )
        if self.body_objects:
            body.extend(iter(self.body_objects))
        actions = {}
        if self.actions:
            actions = {
                "actions": [action.to_dict() for action in self.actions]
            }
        # Iterate over each section, actions or body elements
        return {
            "$schema": self.schema,
            "type": self.card_type,
            "version": self.version,
            "contentType": self.content_type,
            "metadata": {
                "webUrl": "https://contoso.com/tab"
            },
            **properties,
            "body": body,
            **actions
        }


# Actions:
class Submit(CardAction):
    type: str = Field(default='Action.Submit')
    title: str = Field(default='Submit')

class OpenUrl(CardAction):
    type: str = Field(default='Action.OpenUrl')
    title: str
    url: str
    # role: str = Field(default='button')

class ShowCard(CardAction):
    type: str = Field(default='Action.ShowCard')
    title: str
    card: AdaptiveCard

    @property
    def body(self):
        return self.card.body

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        card = self.card.to_adaptive()
        with contextlib.suppress(KeyError):
            del card['version']
            del card['contentType']
            del card['metadata']
        card['@type'] = "MessageCard"
        card['@context'] = "http://schema.org/extensions"
        data['card'] = card
        return data

class ToggleVisibility(CardAction):
    type: str = Field(default='Action.ToggleVisibility')
    targetElements: List[str] = Field(default_factory=list)

class ActionSet(CardElement):
    type: str = Field(default='ActionSet')
    actions: List[CardAction] = Field(default_factory=list)

    def to_adaptive(self):
        return super().to_adaptive()
