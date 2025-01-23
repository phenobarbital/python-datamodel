from typing import Union, Optional
from dataclasses import asdict, InitVar
from pathlib import Path
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


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
    user: InitVar = Field(default='')
    username: InitVar = ''
    hostname: InitVar = ''
    password: str = Field(required=False, default=None, repr=False, is_secret=True)
    auth: dict = Field(required=False, default_factory=dict)
    required_properties: Optional[tuple] = Field(
        repr=False,
        default=default_properties(),
        default_factory=tuple
    )

    def __post_init__(self, user, username, hostname, **kwargs) -> None:  # pylint: disable=W0613,W0221
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
        """create_dsn.

        Description: creates DSN from DSN Format.
        Returns:
            str: DSN.
        """
        params = asdict(self)
        try:
            self.dsn = self.dsn_format.format(**params)
            return self.dsn
        except (AttributeError, ValueError):
            return None

    def get_credentials(self) -> dict:
        """get_credentials.

        Description: Returns credentials for Datasource.
        Returns:
            dict: credentials.
        """
        return self.params()

    def get_parameters(self) -> dict:
        return {}

    @classmethod
    def properties(cls) -> dict:
        """properties.

        Description: Returns fields related to Drivers Supported.
        Returns:
            dict: all required fields for Supported Drivers.
        """

        fields = {}
        for field in cls.required_properties:
            # because tuple is ordered:
            try:
                f = cls.column(cls, field)
            except KeyError:
                continue  # Field Missing on Driver:
            secret = False
            if 'is_secret' in f.metadata:
                secret = f.metadata["is_secret"]
            title = field
            if 'title' in f.metadata:
                title = f.metadata['title']
            required = False
            if 'required' in f.metadata:
                required = f.metadata['required']
            f = {
                "name": field,
                "title": title,
                "required": required,
                "is_secret": secret
            }
            value = getattr(cls, field)
            default = hasattr(f, 'default')
            if not value and default:
                value = f.default
            if value:
                f["value"] = value
            fields[field] = f
        return {
            "driver": cls.driver,
            "name": cls.name,
            "icon": cls.icon,
            "dsn_format": cls.dsn_format,
            "fields": fields
        }


def jdbc_properties() -> tuple:
    return ('host', 'port', 'user', 'password', 'database', 'dsn', 'jar', 'classpath')

class jdbcDriver(BaseModel):
    driver: str = 'jdbc'
    name: str
    provider: str = Field(required=False, default='oracle')
    host: str
    port: Union[str, int]
    username: InitVar = ''
    user: str = Field(required=False, default=None, repr=True)
    password: str = Field(required=False, default=None, repr=False)
    database: str
    dsn_format: str = None
    jar: Union[list, str] = Field(Required=True)
    classpath: Path = Field(Required=False)
    required_properties: Optional[Union[list, tuple]] = Field(
        repr=False, default=jdbc_properties(), default_factory=tuple
    )

    def __post_init__(self, username, *args, **kwargs):
        if isinstance(self.jar, str):
            self.jar = [Path(self.jar)]
        if self.jar and not self.classpath:
            self.classpath = self.jar[0].dirname
        super(jdbcDriver, self).__post_init__(*args, **kwargs)

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

try:
    jdbc_default = jdbcDriver(
        provider='oracle',
        database='xe',
        user='oracle',
        password='oracle',
        host='127.0.0.1',
        port=1521,
        jar='/Users/jlara/.m2/repository/com/oracle/ojdbc/ojdbc8/',
        classpath='/Users/jlara/.m2/repository/com/oracle/ojdbc/ojdbc8/ojdbc8-'
    )
    print('JDBC > ', jdbc_default)
except ValueError:
    jdbc_default = None
except Exception as e:
    print('ERROR > ', e, type(e))
    print('PAYLOAD > ', e.payload)
    jdbc_default = None

try:
    base_driver = BaseDriver(
        driver='asyncdb',
        user='admin',
        password='admin',
        name='asyncdb_test',
        hostname=''
    )
    print('BASE DRIVER > ', base_driver)
except ValidationError as e:
    print(e.payload)
