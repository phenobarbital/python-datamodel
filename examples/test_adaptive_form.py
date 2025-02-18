from datamodel.adaptive.models import AdaptiveCard, InputText, InputNumber, Submit
from datamodel.parsers.json import json_encoder

# Create the Adaptive Card
card = AdaptiveCard(
    title="User Registration",
    summary="Please fill out the form to register."
)

# Add input fields
card.add_body_element(InputText(id="first_name", label="First Name"))
card.add_body_element(InputText(id="last_name", label="Last Name"))
card.add_body_element(InputText(id="username", label="Username", isRequired=True, errorMessage="Username is required"))
card.add_body_element(InputNumber(id="age", label="Age"))

# Add submit button
title = "Submit"
submit_action = Submit(title=title)
card.add_action(submit_action)

# Convert to AdaptiveCard JSON format
adaptive_card_json = card.to_adaptive()
print(json_encoder(adaptive_card_json))
