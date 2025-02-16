from uuid import UUID, uuid4
from typing import List, Dict, Any, Optional, Union
import contextlib
from ..base import BaseModel, Field, register_renderer

def auto_uuid(*args, **kwargs):  # pylint: disable=W0613
    return uuid4()

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
                item.to_adaptive() for item in self.items if isinstance(item, CardElement)
            ],  # Prevent duplicates
            "width": self.width
        }

class ColumnSet(CardElement):
    """A set of columns."""
    type: str = Field(default='ColumnSet')
    columns: List[Column] = Field(default_factory=list)

    def add_column(self, column: Column):
        self.columns.append(column)

    def to_adaptive(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "columns": [column.to_adaptive() for column in self.columns]
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

class FactSet(CardElement):
    """A set of facts."""
    type: str = Field(default='FactSet')
    facts: List[FactElement] = Field(default_factory=list)

    def to_adaptive(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "facts": [fact.to_dict() for fact in self.facts]
        }

class Image(CardElement):
    type: str = Field(default='Image')
    url: str
    size: Optional[str] = None
    style: Optional[str] = None
    altText: Optional[str] = None

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
    body: List[CardElement] = Field(default_factory=list)
    body_objects: List[Dict[str, Any]] = Field(default_factory=list, repr=False)
    actions: List[CardAction] = Field(default_factory=list)
    sections: list[CardSection] = Field(default_factory=list)
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
