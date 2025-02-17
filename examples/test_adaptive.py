from datamodel.adaptive.models import (
    AdaptiveCard,
    TextBlock,
    Image,
    Column,
    ColumnSet,
    FactSet,
    ShowCard,
    Submit,
    Media,
    OpenUrl,
    InputDate,
    InputText,
    Table,
    TableCell
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


### Adaptive Card with a Video and Open URL on a Button:
activity = AdaptiveCard(
    title="Adaptive Card with a Video",
    summary="This card has a video and a button to open a URL"
)
colset = activity.add_body_element(
    ColumnSet()
)
media = Media()
media.add_source(
    source="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
)
colset.create_column(
    media
)
activity.add_action(
    OpenUrl(title="View", url="https://navigator.trocgdigital.io/")
)

# Export Adaptive Card:
data = activity.to_adaptive()
print(data)
print('================')
# JSON representation:
print(json_encoder(data))


print('================')
### Adaptive Card with Pie Chart as Background Image and a Table of Contents:
activity = AdaptiveCard(
    title="Example Pie Chart with Table.",
    summary="This card has Background Image and a Table of Contents",
    minHeight="500px",
)
activity.add_background(
    "https://imgix.ranker.com/user_node_img/50059/1001172544/original/d-photo-u1?auto=format&q=60&fit=crop&fm=pjpg&dpr=2&w=500"
)
table = Table()
table.new_row(
    [
        TableCell(
            items=[
                TextBlock(
                    text="Name",
                    weight="bolder"
                )
            ]
        ),
        TableCell(
            items=[
                TextBlock(
                    text="Value",
                    weight="bolder"
                )
            ]
        )
    ]
)
table.new_row(
    [
        TableCell(
            items=[
                TextBlock(
                    text="Item 1",
                )
            ]
        ),
        TableCell(
            items=[
                TextBlock(
                    text="70%",
                )
            ]
        )
    ]
)
table.new_row(
    [
        TableCell(
            items=[
                TextBlock(
                    text="Item 2",
                )
            ]
        ),
        TableCell(
            items=[
                TextBlock(
                    text="20%",
                )
            ]
        )
    ]
)
table.new_row(
    [
        TableCell(
            items=[
                TextBlock(
                    text="Item 3",
                )
            ]
        ),
        TableCell(
            items=[
                TextBlock(
                    text="10%",
                )
            ]
        )
    ]
)
activity.add_body_element(
    table
)
activity.add_action(
    OpenUrl(title="View More ...", url="https://navigator.trocgdigital.io/")
)
# Export Adaptive Card:
data = activity.to_adaptive()
print(data)
print('================')
# JSON representation:
print(json_encoder(data))
