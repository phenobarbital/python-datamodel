from typing import Any, List, Optional, Union
from html import escape
from datetime import datetime
from ..base import BaseModel, Field, register_renderer


class URL(BaseModel):
    """
    Corresponds to the JSON-LD "URL" type.
    https://schema.org/URL
    """
    url: str

    class Meta:
        schema_type: str = "URL"

class JobTitle(BaseModel):
    """
    The job title of the person (for example, Financial Manager).
    http://schema.org/jobTitle

    Example:
    "jobTitle": {
        "@type": "DefinedTerm",
        "inDefinedTermSet": "https://targetjobs.co.uk/careers-advice/job-descriptions",
        "termCode": "277133-aid-workerhumanitarian-worker-job-description",
        "name": "Aid worker/humanitarian worker",
        "url": "https://targetjobs.co.uk/careers-advice/job-descriptions/277133-aid-workerhumanitarian-worker-job-description"
    }
    """  # noqa
    name: str
    url: str
    inDefinedTermSet: str
    termCode: str

    class Meta:
        schema_type: str = "JobTitle"


class PostalAddress(BaseModel):
    """
    Corresponds to the JSON-LD "Address" type.
    https://schema.org/PostalAddress

    Example:
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Seattle",
            "addressRegion": "WA",
            "postalCode": "98052",
            "streetAddress": "20341 Whitworth Institute 405 N. Whitworth"
        }
    """
    streetAddress: str
    addressLocality: str
    addressRegion: str
    postalCode: str
    addressCountry: str
    postOfficeBoxNumber: Optional[str]
    telephone: Optional[str]

    class Meta:
        schema_type: str = "PostalAddress"


class GeoCoordinates(BaseModel):
    """
    Corresponds to the JSON-LD "GeoCoordinates" type.
    https://schema.org/GeoCoordinates

    Properties:
    latitude: The latitude of a location. For example 37.42242 (WGS 84).
    longitude: The longitude of a location. For example -122.08585 (WGS 84).
    elevation: The elevation of a location (WGS 84).
       Values may be of the form 'NUMBER UNIT_OF_MEASUREMENT' (e.g., '1,000 m')
       while numbers alone should be assumed to be a value in meters.

    Example:
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": "47.603",
            "longitude": "-122.329"
        }
    """
    latitude: float
    longitude: float
    elevation: Optional[float]

    class Meta:
        schema_type: str = "GeoCoordinates"


class Person(BaseModel):
    """
    Corresponds to the JSON-LD "Person" type.
    https://schema.org/Person

    example:
    {
        "@context": "http://schema.org/",
        "@type": "Person",
        "name": "Jane Doe",
        "jobTitle": "Professor",
        "telephone": "(425) 123-4567",
        "url": "http://www.janedoe.com"
    }
    """
    name: str = Field(required=True)
    image: Union["ImageObject", str, None] = None
    jobTitle: Optional[JobTitle]
    telephone: Optional[str] = None
    url: Optional[str] = None
    sameAs: Optional[str] = None

    class Meta:
        schema_type: str = "Person"


class ImageObject(BaseModel):
    """
    Corresponds to the JSON-LD "ImageObject" type.
    https://schema.org/ImageObject
    """
    name: str
    url: str = Field(required=True)
    width: int = 0
    height: int = 0
    caption: str = ""

    class Meta:
        schema_type: str = "ImageObject"


class Recipe(BaseModel):
    """
    Corresponds to the JSON-LD "Recipe" type.
    https://schema.org/Recipe
    """
    name: str
    image: Union["ImageObject", str, None] = None
    datePublished: Optional[str] = None
    description: Optional[str] = None
    prepTime: Optional[str] = None
    cookTime: Optional[str] = None
    totalTime: Optional[str] = None
    recipeIngredient: List[str] = Field(default_factory=list)
    recipeInstructions: List[Any] = Field(default_factory=list)
    recipeCategory: List[str] = Field(default_factory=list)
    recipeCuisine: List[str] = Field(default_factory=list)

    class Meta:
        schema_type: str = "Recipe"


class NutritionInformation(BaseModel):
    """
    Example of a NutritionInformation data model.
        "nutrition": {
                "@type": "NutritionInformation",
                "calories": "512.2 calories",
                "carbohydrateContent": "67.8 g",
                "cholesterolContent": "30.5 mg",
                "fatContent": "26.7 g",
                "fiberContent": "5 g",
                "proteinContent": "3.6 g",
                "saturatedFatContent": "11.1 g",
                "servingSize": null,
                "sodiumContent": "240.8 mg",
                "sugarContent": "40.3 g",
                "transFatContent": null,
                "unsaturatedFatContent": null
        },
    """
    calories: str
    carbohydrateContent: str
    cholesterolContent: str
    fatContent: str
    fiberContent: str
    proteinContent: str
    saturatedFatContent: str
    servingSize: str
    sodiumContent: str
    sugarContent: str
    transFatContent: str
    unsaturatedFatContent: str

    class Meta:
        schema_type: str = "NutritionInformation"

class Organization(BaseModel):
    name: str = Field(required=True)
    url: str
    sameAs: Optional[List[str]] = None
    logo: Optional[ImageObject] = None

    class Meta:
        schema_type = "Organization"

class Rating(BaseModel):
    """
    Corresponds to the JSON-LD "Rating" type.
    https://schema.org/Rating
    """
    ratingValue: str = Field(required=True)
    bestRating: str
    worstRating: str

    class Meta:
        schema_type = "Rating"


class AggregateRating(BaseModel):
    """
    Corresponds to the JSON-LD "AggregateRating" type.
    https://schema.org/AggregateRating
    """
    ratingValue: str = Field(required=True)
    reviewCount: str

    class Meta:
        schema_type = "AggregateRating"


class Product(BaseModel):
    """
    Corresponds to the JSON-LD "Product" type.
    https://schema.org/Product

    Example:
        {
        "@context": "https://schema.org",
        "@type": "Product",
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "3.5",
            "reviewCount": "11"
        },
        "description": "0.7 cubic feet countertop microwave.",
        "name": "Kenmore White 17\" Microwave",
        "image": "kenmore-microwave-17in.jpg",
        "offers": {
            "@type": "Offer",
            "availability": "https://schema.org/InStock",
            "price": "55.00",
            "priceCurrency": "USD"
        },
        }
    """
    name: str = Field(required=True)
    brand: str
    manufacturer: str
    material: str
    model: str
    award: str
    category: str
    gtin: str
    sku: str
    aggregateRating: Optional[AggregateRating]

    class Meta:
        schema_type = "Product"

class Review(BaseModel):
    """
    Corresponds to the JSON-LD "Review" type.
    https://schema.org/Review

    Example:
        {
            "@type": "Review",
            "datePublished": "2009-10-15T16:20:23.473Z",
            "reviewBody": "My words from 2008 still hold true today.",
            "reviewRating": {
                "@type": "Rating",
                "worstRating": "1",
                "bestRating": "5",
                "ratingValue": 5
            },
            "author": {
                "@type": "Person",
                "name": "RCLYMA",
                "image": null,
                "sameAs": "https://www.allrecipes.com/cook/575406/"
            }
        }
    """
    itemReviewed: Optional[Product]
    reviewRating: Rating
    reviewBody: str = Field(default='')
    author: Person
    datePublished: datetime
    publisher: Organization

    class Meta:
        schema_type = "Review"


class VideoObject(BaseModel):
    """
    Corresponds to the JSON-LD "VideoObject" type.
    https://schema.org/VideoObject

    Example:
        "video": {
            "@context": "http://schema.org",
            "@type": "VideoObject",
            "name": "Apple Pie by Grandma Ople",
            "description": "Learn how to make Grandma Ople's apple pie.",
            "uploadDate": "2012-05-09T09:07:12.148Z",
            "duration": "PT4M4.744S",
            "thumbnailUrl": "https://imagesvc.meredithcorp.io/v3/mm/image?url=https%3A%2F%2Fcf-images.us-east-1.prod.boltdns.net%2Fv1%2Fstatic%2F1033249144001%2F571fbd8d-66c7-4521-b002-cbb53ace86e9%2Ff253b5d1-edaf-4dc7-8f0c-954a4259d97f%2F160x90%2Fmatch%2Fimage.jpg",
            "publisher": {
                "@type": "Organization",
                "name": "Allrecipes",
                "url": "https://www.allrecipes.com",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://www.allrecipes.com/img/logo.png",
                    "width": 209,
                    "height": 60
                },
                "sameAs": [
                    "https://www.facebook.com/allrecipes",
                    "https://twitter.com/Allrecipes",
                    "https://www.pinterest.com/allrecipes/",
                    "https://www.instagram.com/allrecipes/"
                ]
            },
            "embedUrl": "https://players.brightcove.net/1033249144001/default_default/index.html?videoId=1629100183001"
        }
    """  # noqa
    name: str = Field(required=True)
    description: str = ''
    uploadDate: datetime
    duration: str
    thumbnailUrl: str
    publisher: Organization
    embedUrl: str

    class Meta:
        schema_type = "VideoObject"


class AdministrativeArea(BaseModel):
    """
    Corresponds to the JSON-LD "AdministrativeArea" type.
    https://schema.org/AdministrativeArea
    """
    name: str = Field(required=True)
    geo: Optional[GeoCoordinates]
    branchCode: Optional[str]

    class Meta:
        schema_type: str = "AdministrativeArea"

class Audience(BaseModel):
    """
    Corresponds to the JSON-LD "Audience" type.
    https://schema.org/Audience
    """
    name: str = Field(required=True)
    audienceType: str
    geographicArea: Optional[AdministrativeArea]

    class Meta:
        schema_type: str = "Audience"


class Place(BaseModel):
    address: PostalAddress

    class Meta:
        schema_type = "Place"

class QuantitativeValue(BaseModel):
    value: float
    unitText: str

    class Meta:
        schema_type = "QuantitativeValue"

class MonetaryAmount(BaseModel):
    currency: Union[str, float]
    value: QuantitativeValue

    class Meta:
        schema_type = "MonetaryAmount"

class JobPosting(BaseModel):
    title: str
    description: str
    hiringOrganization: Organization
    datePosted: str
    validThrough: str
    jobLocation: Optional[Place]
    baseSalary: Optional[MonetaryAmount]
    qualifications: str
    skills: List[str]
    responsibilities: str
    educationRequirements: str
    experienceRequirements: str

    class Meta:
        schema_type = "JobPosting"


@register_renderer("ImageObject")
def render_imageobject(model: "BaseModel", top_level: bool) -> str:
    """
    Render an ImageObject in a custom way:
      <div typeof="ImageObject">
        <h2 property="name">...</h2>
        <img src="..." alt="..." property="contentUrl"/>
        ...
      </div>
    """
    # You can read fields from the model (like name, url, caption, etc.).
    # If you used 'url' as the field that is the image's src, we can do:
    name = getattr(model, "name", None)  # or None if not present
    url = getattr(model, "url", None)
    caption = getattr(model, "caption", None)
    width = getattr(model, "width", None)
    height = getattr(model, "height", None)

    schema_type = getattr(model.Meta, 'schema_type', model.__class__.__name__)

    container_open = ""
    if top_level:
        container_open = f'<div vocab="https://schema.org/" typeof="{escape(schema_type)}">'  # noqa
    else:
        # when nested, we might do property="image" or property=schema_type
        container_open = f'<div property="{escape(schema_type)}" typeof="{escape(schema_type)}">'  # noqa

    pieces = [container_open]

    # Render name as <h2 property="name">Name</h2> if present
    if name:
        name_esc = escape(str(name))
        pieces.append(f'<h2 property="name">{name_esc}</h2>')

    # Now create an <img> that has property="contentUrl" or "url"
    if url:
        url_esc = escape(str(url))
        caption_esc = escape(str(caption or ""))
        # alt can come from caption
        snippet = f'<img property="contentUrl" src="{url_esc}" alt="{caption_esc}"'
        if width:
            snippet += f' width="{escape(str(width))}"'
        if height:
            snippet += f' height="{escape(str(height))}"'
        snippet += ' />'
        pieces.append(snippet)

    # If we have other fields not individually handled, we could do a fallback
    # to the normal field iteration. But for brevity, let's omit that here.
    # E.g. leftover = model.render_remaining_fields(…)
    # pieces.append(leftover)

    pieces.append('</div>')
    return "\n".join(pieces)


@register_renderer("GeoCoordinates")
def render_geocoordinates(model: "BaseModel", top_level: bool) -> str:
    """
    Custom renderer for GeoCoordinates:
      <div property="geo" typeof="GeoCoordinates">
          <meta property="latitude" content="40.75"/>
          <meta property="longitude" content="-73.98"/>
          ...
      </div>
    """
    lat = getattr(model, "latitude", None)
    lng = getattr(model, "longitude", None)
    elevation = getattr(model, "elevation", None)

    schema_type = getattr(model.Meta, 'schema_type', model.__class__.__name__)
    if top_level:
        container_open = f'<div vocab="https://schema.org/" typeof="{escape(schema_type)}">'  # noqa
    else:
        container_open = f'<div property="{escape(schema_type)}" typeof="{escape(schema_type)}">'  # noqa

    pieces = [container_open]

    # For numeric fields, we might prefer <meta ... content="..."/>
    if lat is not None:
        pieces.append(
            f'<meta property="latitude" content="{escape(str(lat))}" />'
        )
    if lng is not None:
        pieces.append(
            f'<meta property="longitude" content="{escape(str(lng))}" />'
        )
    if elevation is not None:
        pieces.append(
            f'<meta property="elevation" content="{escape(str(elevation))}" />'
        )

    pieces.append('</div>')
    return "\n".join(pieces)
