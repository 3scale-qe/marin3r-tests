"""Module which initializes Dynaconf"""

from dynaconf import Dynaconf, Validator

from testsuite.config.tools import fetch_route, fetch_secret


# pylint: disable=too-few-public-methods
class DefaultValueValidator(Validator):
    """Validator which will run default function only when the original value is missing"""

    def __init__(self, name, default, **kwargs) -> None:
        super().__init__(
            name,
            ne=None,
            messages={
                "operations": (
                    "{name} must {operation} {op_value} but it is {value} in env {env}. "
                    "You might be missing tools on the cluster."
                )
            },
            default=default,
            when=Validator(name, must_exist=False),
            **kwargs
        )


settings = Dynaconf(
    environments=True,
    lowercase_read=True,
    load_dotenv=True,
    settings_files=["config/settings.yaml", "config/secrets.yaml"],
    envvar_prefix="MARIN3R",
    merge_enabled=True,
    validators=[
        Validator("envoy.image", must_exist=True),
        Validator("cfssl", must_exist=True),
    ],
    loaders=["dynaconf.loaders.env_loader", "testsuite.config.openshift_loader"],
)
