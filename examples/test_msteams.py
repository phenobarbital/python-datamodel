from typing import Optional, List
import uuid
from datetime import datetime
from datamodel import BaseModel, Field


def auto_uuid(*args, **kwargs):  # pylint: disable=W0613
    return uuid.uuid4()


def now():
    return datetime.now()

class TeamsChannel(BaseModel):
    name: str
    channel_id: str
    team_id: str

class TeamsChat(BaseModel):
    name: str
    chat_id: str
    team_id: str

class TeamsWebhook(BaseModel):
    uri: str = Field(required=True)


class TeamsTarget(BaseModel):
    os: str = Field(default='default')
    uri: str = Field(required=True)

class TeamsAction(BaseModel):
    name: str = Field(required=False, default=None)
    targets: list[TeamsTarget] = Field(default_factory=list)

class TeamsSection(BaseModel):
    activityTitle: str = Field(required=False, default=None)
    activitySubtitle: str = Field(required=False, default=None)
    activityImage: str = Field(required=False, default=None)
    facts: list[dict] = Field(required=False, default_factory=list)
    text: str = Field(required=False, default=None)
    potentialAction: list[TeamsAction] = Field(
        required=False,
        default=None,
        default_factory=list
    )

    def addFacts(self, facts: list):
        self.facts = facts

    def to_adaptative(self):
        items = []

        if self.activityTitle:
            items.append({
                "type": "TextBlock",
                "size": "medium",
                "weight": "bolder",
                "text": self.activityTitle
            })
        if self.activitySubtitle:
            items.append({
                "type": "TextBlock",
                "spacing": "none",
                "weight": "bold",
                "text": self.activitySubtitle
            })
        if self.activityImage:
            items.append({
                "type": "Image",
                "size": "small",
                "url": self.activityImage
            })
        if self.facts:
            items.append({
                "type": "FactSet",
                "facts": self.facts
            })

        return {
            "type": "Container",
            "items": items
        }

class CardAction(BaseModel):
    type: str = Field(required=False, default=None)
    title: str = Field(required=False, default=None)
    data: dict = Field(required=False, default_factory={})


class TeamsCard(BaseModel):
    card_id: uuid.UUID = Field(required=False, default=auto_uuid, repr=False)
    content_type: str = Field(
        required=False,
        default="application/vnd.microsoft.card.adaptive",
        repr=False
    )
    summary: str
    sections: list[TeamsSection] = Field(required=False, default_factory=list)
    text: str = Field(required=False, default=None)
    title: str = Field(required=False, default=None)
    body_objects: List[dict] = Field(
        required=False,
        default_factory=dict,
        repr=False
    )
    actions: List[CardAction] = Field(required=False, default_factory=list, repr=False)

    def addAction(self, type: str, title: str, **kwargs):
        self.actions.append(
            CardAction(type, title, data=kwargs)
        )

    def addSection(self, **kwargs):
        section = TeamsSection(**kwargs)
        self.sections.append(section)
        return section

    def addInput(
        self,
        id: str,
        label: str,
        is_required: bool = False,
        errorMessage: str = None,
        style: str = None
    ):
        element = {
            "type": "Input.Text",
            "id": id,
            "label": label,
            "isRequired": is_required,
            "errorMessage": errorMessage
        }
        if style is not None:
            element["style"] = style
        self.body_objects.append(
            element
        )

    def to_dict(self):
        data = super(TeamsCard, self).to_dict()
        del data['card_id']
        del data['body_objects']
        del data['actions']
        data['@type'] = "MessageCard"
        data['@context'] = "http://schema.org/extensions"
        return data

    def to_adaptative(self) -> dict:
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
        if self.text:
            body.append({
                "type": "TextBlock",
                "text": self.text,
                "wrap": True
            })
        if self.sections:
            sections = []
            body.append({
                "type": "Container",
                "items": sections
            })
            sections.extend(section.to_adaptative() for section in self.sections)
        if self.body_objects:
            body.extend(iter(self.body_objects))
        if self.actions:
            actions = [action.to_dict() for action in self.actions]
            body.append({
                "actions": actions
            })

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.6",
            "contentType": "application/vnd.microsoft.card.adaptive",
            "metadata": {
                "webUrl": "https://contoso.com/tab"
            },
            "body": body
        }


def test_cards():
    msg = TeamsCard(
        text='🛑⚠️✅  Mensaje de PRUEBAS enviado a Navigator Teams',
        summary='Card Summary'
    )
    #  add a section:
    msg.addSection(
        activityTitle='Test Activity Title',
        text='Potential text on Section'
    )
    msg.addInput(
        id="UserVal", label='Username'
    )
    msg.addInput(
        id="PassVal",
        label='Password',
        style="Password"
    )
    #  add an action:
    msg.addAction(
        type='Action.Submit',
        title="Login into NAV",
        id="LoginVal"
    )
    print(msg.to_dict())
    print(msg.to_adaptative())

if __name__ == '__main__':
    test_cards()
