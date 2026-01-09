#!/usr/bin/env python3
"""
Validate that docker-compose.frontend-dev.yml contains all required
environment variables defined in app/core/config.py Settings class.

This ensures the frontend team's docker-compose setup stays in sync
with backend requirements.
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


def get_required_settings_fields() -> set[str]:
    """
    Collects the names of fields declared without a default value on the Settings subclass in app/core/config.py.

    Reads the project's Settings (a BaseSettings subclass) and returns the set of attribute names that are required (i.e., declared without an assignment/default).

    Returns:
        set[str]: Field names that are required (have no default value) as declared in the Settings class.

    Notes:
        Exits the process if the config.py file cannot be found.
    """
    config_file = Path(__file__).parent.parent / "app" / "core" / "config.py"

    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        sys.exit(1)

    required_fields = set()
    content = config_file.read_text()
    in_settings_class = False

    for line in content.split("\n"):
        if "class Settings(BaseSettings):" in line:
            in_settings_class = True
            continue

        if in_settings_class:
            # End of class
            if line and not line.startswith(" ") and not line.startswith("\t"):
                break

            # Skip comments, empty lines, and model_config
            if (
                not line.strip()
                or line.strip().startswith("#")
                or "model_config" in line
            ):
                continue

            # Extract field name without default value (required fields)
            stripped = line.strip()
            if ":" in stripped and not stripped.startswith("def"):
                field_name = stripped.split(":")[0].strip()
                if "=" not in stripped:  # No default = required
                    required_fields.add(field_name)

    return required_fields


def get_compose_env_vars() -> set[str]:
    """
    Collects environment variable names used by the `fastapi` service in docker-compose.frontend-dev.yml.

    Searches the `fastapi` service for an `env_file` reference (reads referenced files) or inline `environment` entries and extracts variable names. Exits the process with status 1 if the compose file or any referenced env file is missing.

    Returns:
        set[str]: A set of environment variable names found in the compose configuration.
    """
    compose_file = Path(__file__).parent.parent / "docker-compose.frontend-dev.yml"

    if not compose_file.exists():
        print(f"❌ Compose file not found: {compose_file}")
        sys.exit(1)

    with open(compose_file) as f:
        compose = yaml.safe_load(f)

    fastapi_service = compose.get("services", {}).get("fastapi", {})
    compose_env_vars = set()

    # Check if using env_file reference
    if "env_file" in fastapi_service:
        print("ℹ️  docker-compose.frontend-dev.yml uses env_file reference")
        print("   Checking the referenced .env.frontend-dev file...\n")

        env_files = fastapi_service["env_file"]
        if isinstance(env_files, str):
            env_files = [env_files]

        for env_file_path in env_files:
            env_file = Path(__file__).parent.parent / env_file_path
            if not env_file.exists():
                print(f"❌ Referenced env file not found: {env_file}")
                sys.exit(1)

            content = env_file.read_text()
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    var_name = line.split("=")[0].strip()
                    compose_env_vars.add(var_name)

    # Check inline environment variables
    elif "environment" in fastapi_service:
        for env_entry in fastapi_service["environment"]:
            if "=" in env_entry:
                var_name = env_entry.split("=", 1)[0].strip()
                compose_env_vars.add(var_name)

    return compose_env_vars


def main():
    """
    Validate that every required field declared in the Settings class of app/core/config.py is present as an environment variable in docker-compose.frontend-dev.yml.

    Prints a summary of required fields, environment variables found in the compose file, any missing required variables (and a failure message), and any additional variables (informational).

    Returns:
        int: 0 if all required environment variables are present, 1 if any required variables are missing.
    """
    print("🔍 Validating frontend docker-compose environment variables...\n")

    # Get required fields from Settings
    required_fields = get_required_settings_fields()
    print(f"📋 Found {len(required_fields)} required fields in Settings class:")
    for field in sorted(required_fields):
        print(f"   • {field}")
    print()

    # Get env vars from compose file
    compose_env_vars = get_compose_env_vars()
    print(f"📋 Found {len(compose_env_vars)} environment variables in compose:")
    for var in sorted(compose_env_vars):
        print(f"   • {var}")
    print()

    # Check for missing variables
    missing = required_fields - compose_env_vars

    if missing:
        print("❌ VALIDATION FAILED\n")
        print(f"Missing {len(missing)} required environment variable(s):\n")
        for var in sorted(missing):
            print(f"   ❌ {var}")
        print("\n⚠️  Add these to docker-compose.frontend-dev.yml or .env.frontend-dev")
        return 1

    # Check for extra variables (informational)
    extra = compose_env_vars - required_fields
    if extra:
        print(f"ℹ️  {len(extra)} additional variables (optional or service-specific):")
        for var in sorted(extra):
            print(f"   • {var}")
        print()

    print("✅ VALIDATION PASSED")
    print("All required environment variables are present!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
