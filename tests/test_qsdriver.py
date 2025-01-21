from typing import List, Optional, Union
from dataclasses import InitVar
from datetime import datetime
from pathlib import Path
import pytest
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError

# For demonstration purposes, here are the models re‐declared:
def default_properties() -> tuple:
    return ('host', 'port', 'user', 'username', 'password')

class BaseDriver(BaseModel):
    """BaseDriver.

    Description: Base class for all required datasources.
    """
    driver: str = Field(required=True, primary_key=True)
    driver_type: str = Field(
        required=True,
        default='asyncdb',
        comment="type of driver, can be asyncdb, qs or REST"
    )
    name: str = Field(required=False, comment='Datasource name, default to driver.')
    description: str = Field(comment='Datasource Description', repr=False)
    icon: str = Field(required=False, comment='Icon Path for Datasource.', repr=False)
    dsn: str = Field(default=None)
    dsn_format: str = Field(required=False, default=None, repr=False)
    user: InitVar = Field(default='')  # using InitVar here is optional for testing
    username: str = Field(default='')
    password: str = Field(required=False, default=None, repr=False, is_secret=True)
    auth: dict = Field(required=False, default_factory=dict)
    required_properties: Optional[Union[list, tuple]] = Field(
        repr=False, default=default_properties(), default_factory=tuple
    )

    def __post_init__(self, user, **kwargs) -> None:
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
        super(BaseDriver, self).__post_init__()

    def create_dsn(self) -> str:
        params = self.to_dict()  # or asdict(self)
        try:
            self.dsn = self.dsn_format.format(**params)
            return self.dsn
        except (AttributeError, ValueError):
            return None

    def params(self) -> dict:
        return {k: getattr(self, k) for k in ["driver", "username", "password"]}

def jdbc_properties() -> tuple:
    return ('host', 'port', 'user', 'password', 'database', 'dsn', 'jar', 'classpath')

class jdbcDriver(BaseDriver):
    driver: str = 'jdbc'
    name: str
    provider: str = Field(required=False, default='oracle')
    host: str
    port: Union[str, int]
    username: object = Field(default='')  # using InitVar-like (for testing, we use a simple field)
    password: str = Field(required=False, default=None, repr=False)
    database: str = Field(required=True)
    dsn_format: str = Field(required=False, default=None)
    jar: List[Path] = Field(required=True)
    classpath: Path = Field(required=False)
    required_properties: Optional[Union[list, tuple]] = Field(
        repr=False, default=jdbc_properties(), default_factory=tuple
    )

    def __post_init__(self, user: str = "", **kwargs):
        # If jar is a string, convert it to a list with one Path element.
        if isinstance(self.jar, str):
            self.jar = [Path(self.jar)]
        elif isinstance(self.jar, list):
            self.jar = [Path(p) if isinstance(p, str) else p for p in self.jar]
        # If jar is set and classpath is missing, assume classpath is the dirname of the first jar.
        if self.jar and not self.classpath:
            self.classpath = self.jar[0].parent
        super(jdbcDriver, self).__post_init__(user, **kwargs)

    def params(self) -> dict:
        return {
            "driver": self.provider,
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "jar": self.jar,
            "classpath": self.classpath
        }
# --- End of model declarations ---

# Now we create our pytest functions.

def test_jdbcdriver_valid():
    payload = {
        "provider": "oracle",
        "database": "xe",
        "user": "oracle",
        "password": "oracle",
        "host": "127.0.0.1",
        "port": 1521,
        "jar": "/tmp/ojdbc8/",
        "classpath": "/tmp/ojdbc8/ojdbc8-"
    }
    driver = jdbcDriver(**payload)
    # Check that fixed attributes are set correctly
    assert driver.driver == "jdbc"
    assert driver.provider == "oracle"
    assert driver.host == "127.0.0.1"
    # Port should be stored as the provided type (e.g. number)
    assert driver.port == 1521
    # jar must be converted: if provided as a string, it becomes a list of Path objects.
    assert isinstance(driver.jar, list)
    for p in driver.jar:
        assert isinstance(p, Path)
    # classpath should be set as the parent of the jar's first element if not provided explicitly.
    assert isinstance(driver.classpath, Path)
    # required_properties should equal the tuple returned by jdbc_properties()
    expected_props = jdbc_properties()
    assert driver.required_properties == expected_props
    # Test that the params() method returns a dictionary with expected keys.
    params = driver.params()
    for key in ["host", "port", "user", "password", "database", "jar", "classpath"]:
        assert key in params

def test_basedriver_valid():
    # Test instantiation of BaseDriver
    payload = {
        "driver": "asyncdb",
        "user": "admin",
        "password": "admin",
        "name": "asyncdb_test"
    }
    driver = BaseDriver(**payload)
    # If name is provided then it remains
    assert driver.name == "asyncdb_test"
    # auth dictionary should be built from username and password.
    expected_auth = {"username": driver.username, "password": driver.password}
    assert driver.auth == expected_auth

def test_basedriver_defaults():
    # Test that if name is not provided in BaseDriver then it defaults to driver value.
    payload = {
        "driver": "asyncdb",
        "user": "admin",
        "password": "admin",
        # name is missing
    }
    driver = BaseDriver(**payload)
    assert driver.name == "asyncdb"
    # username is not empty because user is a InitVar of username
    assert driver.username == payload["user"]
    # auth uses username and password
    assert driver.auth == {"username": "admin", "password": "admin"}

def test_jdbcdriver_missing_required():
    # 'database' is required; omit it to trigger validation error.
    payload = {
        "provider": "oracle",
        "user": "oracle",
        "password": "oracle",
        "host": "127.0.0.1",
        "port": 1521,
        "jar": "/tmp/ojdbc8/",
        "classpath": "/tmp/ojdbc8/ojdbc8-"
    }
    with pytest.raises(ValueError):
        jdbcDriver(**payload)

if __name__ == "__main__":
    pytest.main()
