from typing import Union, Optional
from dataclasses import InitVar
from pathlib import Path
from datamodel import BaseModel, Field

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
        repr=False, default=jdbc_properties()
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
except ValueError:
    jdbc_default = None
except Exception as e:
    print('ERROR > ', e, type(e))
    print('PAYLOAD > ', e.payload)
    jdbc_default = None
