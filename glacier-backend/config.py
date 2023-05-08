import os
import dataclasses

# Server code under no circumstances is supposed to run outside a docker container -> environment is consistent


@dataclasses.dataclass
class AnyConfigFromEnv:
    def __init__(self):
        environment = os.environ
        for field in dataclasses.fields(self):
            if field.name.upper() not in environment:
                raise Exception(f'field {field} not found in env')
            if not environment[field.name.upper()]:
                raise Exception(f'field {field} is empty')
            if field.type == int:
                setattr(self, field.name, int(environment[field.name.upper()]))
            else:
                setattr(self, field.name, environment[field.name.upper()])


@dataclasses.dataclass
class DatabaseConfig(AnyConfigFromEnv):
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_pass: str

    def __init__(self):
        super().__init__()


@dataclasses.dataclass
class RenderConfig(AnyConfigFromEnv):
    upload_facility: str
    blender_bin: str

    def __init__(self):
        super().__init__()


@dataclasses.dataclass
class UserAddConfig(AnyConfigFromEnv):
    glacier_user: str
    glacier_password: str

    def __init__(self):
        super().__init__()
