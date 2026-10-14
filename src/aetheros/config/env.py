#  Environment variablesimport os


def get_env(name: str, default=None):
    return os.getenv(name, default)


def require_env(name: str):
    value = os.getenv(name)

    if value is None:
        raise RuntimeError(f"Missing environment variable: {name}")

    return value