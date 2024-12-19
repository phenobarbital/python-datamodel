"""
JSON-LD: Working with microdata types.
"""
from typing import Optional
from datetime import datetime
import pprint
from datamodel import BaseModel, Field
from datamodel.parsers.json import json_encoder

# Example Product model
class Product(BaseModel):
    name: str = Field()

    class Meta:
        schema_type = "Product"

# Example Person model
class Person(BaseModel):
    name: str = Field()

    class Meta:
        schema_type = "Person"

# Example Rating model
class Rating(BaseModel):
    ratingValue: str = Field()

    class Meta:
        schema_type = "Rating"

# Organization model
class Organization(BaseModel):
    name: str = Field()

    class Meta:
        schema_type = "Organization"

# Review model
class Review(BaseModel):
    name: str = Field()
    itemReviewed: Product = Field()
    reviewRating: Rating = Field()
    reviewBody: str = Field()
    author: Person = Field()
    datePublished: datetime = Field()
    publisher: Organization = Field()

    class Meta:
        schema_type = "Review"


# Instanciate Models:
product = Product(name="The Catcher in the Rye")
author = Person(name="John Doe")
rating = Rating(ratingValue="5")
review = Review(
    itemReviewed=product,
    reviewRating=rating,
    name="An interesting story",
    author=author,
    datePublished="2020-03-16"
)

print('Review : ', review)


# Convert Review object to schema representation
review_schema = review.as_schema()

print('Review schema : ', review_schema)

# You can now serialize this to JSON and embed in your HTML:
print("<script type=\"application/ld+json\">")
print(json_encoder(review_schema))
print("</script>")

pp = pprint.PrettyPrinter(width=41, compact=True)
pp.pprint(review_schema)

### Restaurant Reviews Example:

# Restaurant model
class Restaurant(BaseModel):
    name: str = Field()

    class Meta:
        schema_type = "Restaurant"


# Instantiate Models
restaurant = Restaurant(name="Legal Seafood")
author = Person(name="Bob Smith")
rating = Rating(ratingValue="4")
publisher = Organization(name="Washington Times")

review = Review(
    itemReviewed=restaurant,
    reviewRating=rating,
    name="A good seafood place.",
    reviewBody="""
    It is a great experience.
    The ambiance is very welcoming and charming.
    Amazing food and service.
    Staff are extremely knowledgeable and make great recommendations.""",
    author=author,
    publisher=publisher
)

# Convert Review object to schema representation
review_schema = review.as_schema()

print("Review schema :", review_schema)

# Serialize to JSON for embedding into HTML
print("<script type=\"application/ld+json\">")
print(json_encoder(review_schema))
print("</script>")


### Example of Job Posting:
class PostalAddress(BaseModel):
    streetAddress: str = Field()
    addressLocality: str = Field()
    postalCode: str = Field()
    addressCountry: str = Field()

    class Meta:
        schema_type = "PostalAddress"

class Place(BaseModel):
    address: PostalAddress = Field()

    class Meta:
        schema_type = "Place"

class QuantitativeValue(BaseModel):
    value: float = Field()
    unitText: str = Field()

    class Meta:
        schema_type = "QuantitativeValue"

class MonetaryAmount(BaseModel):
    currency: str = Field()
    value: QuantitativeValue = Field()

    class Meta:
        schema_type = "MonetaryAmount"

class Organization(BaseModel):
    name: str = Field()

    class Meta:
        schema_type = "Organization"

class JobPosting(BaseModel):
    title: str = Field()
    description: str = Field()
    hiringOrganization: Organization = Field()
    datePosted: str = Field()
    validThrough: str = Field()
    jobLocation: Place = Field()
    baseSalary: MonetaryAmount = Field()
    qualifications: str = Field()
    skills: str = Field()
    responsibilities: str = Field()
    educationRequirements: str = Field()
    experienceRequirements: str = Field()

    class Meta:
        schema_type = "JobPosting"

# Instantiate the related models
org = Organization(name="ACME Corp")
address = PostalAddress(
    streetAddress="123 Main St",
    addressLocality="Anytown",
    postalCode="12345",
    addressCountry="US"
)
place = Place(address=address)
salary_value = QuantitativeValue(value=60000, unitText="YEAR")
salary = MonetaryAmount(currency="USD", value=salary_value)

job = JobPosting(
    title="Software Engineer",
    description="We are looking for a software engineer to join our team.",
    hiringOrganization=org,
    datePosted="2024-12-31",
    validThrough="2025-03-31",
    jobLocation=place,
    baseSalary=salary,
    qualifications="Bachelor's degree in Computer Science or related field",
    skills="Python, Django, RESTful APIs",
    responsibilities="Develop, test, and maintain software applications.",
    educationRequirements="Bachelor's degree",
    experienceRequirements="2+ years of professional experience"
)

# Convert the JobPosting object to schema representation
job_schema = job.as_schema()

print("<script type=\"application/ld+json\">")
print(json_encoder(job_schema))
print("</script>")
