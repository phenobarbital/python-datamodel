from typing import Optional
from dataclasses import InitVar
from datamodel import BaseModel, Field

def default_properties() -> tuple:
    return ('host', 'port', 'user', 'username', 'password' )

class DataDriver(BaseModel):
    """DataDriver.

    Description: Base class for all required datasources.
    """
    driver: str = Field(required=True, primary_key=True)
    driver_type: str = Field(required=True, default='asyncdb', comment="type of driver, can be asyncdb, qs or REST")
    name: str = Field(required=False, comment='Datasource name, default to driver.')
    description: str = Field(comment='Datasource Description', repr=False)
    icon: str = Field(required=False, comment='Icon Path for Datasource.', repr=False)
    host: str
    port: int
    dsn: str = None
    dsn_format: str = Field(required=False, default=None, repr=False)
    user: InitVar = ''
    username: str = ''
    password: str = Field(required=False, default=None, repr=False, is_secret=True)
    auth: dict = Field(required=False, default_factory=dict)
    required_properties: Optional[tuple] = Field(repr=False, default=default_properties())

    def __post_init__(self, user, **kwargs) -> None: # pylint: disable=W0613,W0221
        if not self.name:
            self.name = self.driver
        if user:
            self.username = user
        self.auth = {
            "username": self.username,
            "password": self.password
        }
        # set DSN (if needed)
        if self.dsn_format is not None and self.dsn is None:
            self.create_dsn()
        super(DataDriver, self).__post_init__()


driver = DataDriver(driver='postgres', name='pg', dsn='', user='pg', password='123', host='localhost', port=5433)
print(driver)
print(driver.required_properties)
