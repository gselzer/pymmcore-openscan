"""
Settings for PyMMCore-OpenScan widgets.

Much of this code is graciously borrowed from
https://github.com/pymmcore-plus/pymmcore-gui/blob/main/src/pymmcore_gui/_settings.py
"""

from __future__ import annotations

import json
import os
import threading
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, cast

from platformdirs import user_data_dir
from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

if TYPE_CHECKING:
    from typing import Any

    from pydantic.fields import FieldInfo

# Follow pymmcore-gui settings
APP_NAME = "pymmcore-openscan"
USER_DATA_DIR = Path(user_data_dir(appname=APP_NAME))
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE_NAME = USER_DATA_DIR / "pmm_settings.json"
TESTING = "PYTEST_VERSION" in os.environ
_GLOBAL_SETTINGS: Settings | None = None


class PyMMCoreOpenScanSettingsSource(PydanticBaseSettingsSource):
    """Loads variables from file json file persisted to disk."""

    @staticmethod
    def exists() -> bool:
        """Return True if the settings file exists."""
        return SETTINGS_FILE_NAME.exists()

    @staticmethod
    def content() -> str:
        """Return the contents of the settings file."""
        return SETTINGS_FILE_NAME.read_text(errors="ignore")

    @staticmethod
    def values() -> dict[str, Any]:
        """Return the contents of the settings file."""
        if not PyMMCoreOpenScanSettingsSource.exists():
            return {}

        if not (content := PyMMCoreOpenScanSettingsSource.content()):
            # file exists but is empty
            return {}

        values = json.loads(content)
        if not isinstance(values, dict):
            raise ValueError("Settings file does not contain a dictionary.")
        return values

    def _read_settings(self) -> dict[str, Any]:
        """Return the settings values from the source."""
        try:
            return PyMMCoreOpenScanSettingsSource.values()
        except Exception as e:
            # Never block the application from starting because of a settings file
            warnings.warn(
                f"Failed to read settings from {SETTINGS_FILE_NAME}: {e}",
                RuntimeWarning,
                stacklevel=2,
            )
        return {}

    def __call__(self) -> dict[str, Any]:
        """Return Settings values for this source."""
        if os.getenv("MMGUI_NO_SETTINGS"):  # pragma: no cover
            return {}
        values = self._read_settings()
        return _good_data_only(Settings, values, warn=True)

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        """Return the value for a field (required by ABC)."""
        # Nothing to do here. Only implement the return statement to make mypy happy
        return None, "", False  # pragma: no cover


def _good_data_only(
    cls: type[BaseModel], data: dict[str, Any], warn: bool = True
) -> dict[str, Any]:
    """Attempt to extract only the good fields from `data` that are valid for `cls`."""
    cleaned: dict[str, Any] = {}
    model_fields = cls.model_fields
    for key, value in data.items():
        if key in model_fields:
            # check whether the value is valid for the field
            field = model_fields[key]
            annotation = field.annotation
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                cleaned[key] = _good_data_only(annotation, value, warn=warn)
            else:
                try:
                    TypeAdapter(field.annotation).validate_python(value)
                    cleaned[key] = value
                except ValidationError as e:
                    if warn:
                        warnings.warn(
                            f"Could not validate key {key!r} from settings file: {e}",
                            RuntimeWarning,
                            stacklevel=2,
                        )
        elif warn:
            # user supplied something that doesn't exist in the model
            # ignore it, but warn the user
            warnings.warn(
                f"Key {key!r} from settings file not found in model.",
                RuntimeWarning,
                stacklevel=2,
            )
            # we still include it for backwards compatibility
            # it could be an additional function that "cleans" settings.
            cleaned[key] = value
    return cleaned


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # don't fail if an extra key is present.  just ignore it
        # (this is important for backwards compatibility)
        # note: this could also be "include", if we want an older version of the app
        # to be able to open a newer version's settings file, without losing data
        extra="ignore",
    )

    bh_dcc_dcu_connector_labels: dict[str, dict[int, str]] = {}
    """Labels for DCC/DCU unit connectors."""
    bh_dcc_dcu_connector_visibility: dict[str, dict[int, bool]] = {}
    """Visibility for DCC/DCU unit connectors."""

    @classmethod
    def instance(cls) -> Settings:
        """Return the singleton instance of the settings."""
        global _GLOBAL_SETTINGS
        if _GLOBAL_SETTINGS is None:
            _GLOBAL_SETTINGS = Settings()
        return _GLOBAL_SETTINGS

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Define the sources and their order for loading the settings values.

        Values are loaded in the order of the sources. Priority is given to earlier
        sources (i.e. values explicitly passed to the constructor take priority,
        then environment variables, then dotenv files, then the user settings from
        SETTINGS_FILE, then file secrets).
        """
        if TESTING:
            # we're running in tests...
            # don't load the user settings, and change env-prefix
            # I started by using a fixture in conftest.py, to patch this method
            # but it's difficult to ensure that it always gets patched in time
            # this is more guaranteed to work
            cast("EnvSettingsSource", env_settings).env_prefix = "PMM_TEST_"
            return (init_settings, env_settings)

        return (
            init_settings,
            env_settings,
            dotenv_settings,
            PyMMCoreOpenScanSettingsSource(settings_cls),
            file_secret_settings,
        )

    def flush(self, timeout: float | None = None) -> None:
        """Write the settings to disk.

        If `timeout` is not None, block until the write is complete, or until the
        timeout is reached.
        """
        if TESTING or os.getenv("MMGUI_NO_SETTINGS"):  # pragma: no cover
            return
        # write in another thread, so we don't block the main thread
        thread = threading.Thread(target=self._write_settings)
        thread.start()
        if timeout:
            thread.join(timeout)

    def _write_settings(self) -> None:
        json_str = self.model_dump_json(indent=2, exclude_defaults=True)
        SETTINGS_FILE_NAME.write_text(json_str, errors="ignore")
