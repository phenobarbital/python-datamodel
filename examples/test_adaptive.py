from datamodel.adaptive.models import (
    AdaptiveCard,
    TextBlock,
    Image,
    Column,
    ColumnSet,
    FactSet,
    ShowCard,
    Submit,
    OpenUrl,
    InputDate,
    InputText,
)
from datamodel.parsers.json import json_encoder


# Sample Acitivity Update:
activity = AdaptiveCard(
    title="Publish Adaptive Card Schema"
)
colset = ColumnSet()
img = Image(
    style='person',
    url='https://pbs.twimg.com/profile_images/3647943215/d7f12830b3c17a5a9e4afcc370e3a37e_400x400.jpeg',
    altText="Matt Hidinger",
    size='small'
)
col = Column()
col.add_item(img)
colset.add_column(
    col
)
col = Column(width='stretch')
col.add_item(
    item=[
        TextBlock(
            text='Matt Hidinger',
            weight='bolder',
            wrap=True
        ),
        TextBlock(
            text='Created {{DATE(2017-02-14T06:08:39Z, SHORT)}}',
            isSubtle=True,
            wrap=True
        )
    ],

)
colset.add_column(
    col
)
activity.add_body_element(colset)
activity.add_text(
    text="Now that we have defined the main rules and features of the format, we need to produce a schema and publish it to GitHub. The schema will be the starting point of our reference documentation."
)
# FactSet:
facts = FactSet(
    facts=[
        {
            "title": "Board:",
            "value": "Adaptive Card"
        },
        {
            "title": "List:",
            "value": "Backlog"
        },
        {
            "title": "Assigned to:",
            "value": "Matt Hidinger"
        },
        {
            "title": "Due date:",
            "value": "Not set"
        }
    ]
)
activity.add_body_element(
    facts
)
## Actions:
# Show Card:
show = ShowCard(
    title="Set due date",
    card=AdaptiveCard(
        body=[
            TextBlock(
                text="Enter your comment"
            ),
            TextBlock(
                text="This is a comment"
            )
        ],
        actions=[
            Submit(
                title="Submit"
            )
        ]
    )
)
print(' NUM > ', len(show.card.actions), show.card.actions)
show.body.append(
    InputDate(
        id="dueDate",
        label="Enter the due date"
    )
)
show.body.append(
    InputText(
        id="comment",
        isMultiline=True,
        label="Enter your comment"
    )
)
activity.add_action(
    show
)
# Add an Action Button:
activity.add_action(
    OpenUrl(title="View", url="https://adaptivecards.io")
)
# Export Adaptive Card:
data = activity.to_adaptive()
print(data)
print('================')
# JSON representation:
print(json_encoder(data))
