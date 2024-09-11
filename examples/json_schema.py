import pprint
from datetime import datetime
import locale
from datamodel import BaseModel, Column
from navigator.ext.locale import LocaleSupport
from navigator import Application

pp = pprint.PrettyPrinter(width=41, compact=True)

l18n = LocaleSupport(
    localization=['en_US', 'es_ES', 'es', 'it_IT', 'de_DE', 'fr_FR'],
    domain='nav'
)
app = Application()
l18n.setup(app)

class Airport(BaseModel):
    iata: str = Column(
        primary_key=True, required=True, label="IATA"
    )
    airport: str = Column(
        required=True, label="airport"
    )
    city: str = Column(
        required=False, label="city"
    )
    country: str = Column(
        required=False, label="country"
    )
    created_by: int = Column(
        required=False, label="created_by"
    )
    created_at: datetime = Column(
        default=datetime.now, repr=False, label="created_at"
    )

    class Meta:
        name: str = 'airports'
        description: str = 'airports'
        title: str = 'airports'
        schema = 'public'
        settings = {
            "showSubmit": True,
            "SubmitLabel": "submit",
            "showCancel": False
        }
        strict = True

localization = 'it_IT'
locale.setlocale(
    locale.LC_ALL, f"{localization}.UTF-8"
)  # set the current localization

trans = l18n.translator(locale=locale, lang=f"{localization}.UTF-8")
print('LOCALE > ', l18n.current_locale())
print('T > ', trans)
d = trans('city')
print(d)
schema = Airport.schema(as_dict=True, locale=trans)
print(schema)
