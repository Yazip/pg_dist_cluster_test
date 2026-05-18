import pathlib
import yaml

CONFIG_FILE = pathlib.Path(__file__).parent / "config.yaml" # config.yaml must be located in the same directory as config.py

def _get_value(data: dict, key: str, context: str = ""):
    """Extracts a key value from a dictionary with a check for existence and None.

    This auxiliary function provides a single data access standard configurations.
    If the key is missing or its value is None, a clear exception is generated indicating
    the context (where exactly the error occurred).

    Args:
        data (dict): A dictionary with configuration data.
        key (str): The key whose value needs to get.
        context (str, optional): A string description of the context, used to generate
            the error message. By default, an empty string.

    Returns:
        Any: The value associated with the specified key.

    Raises:
        KeyError: If the key is missing from the `data` dictionary.
        ValueError: If the key value exists but is `None`.
    """
    if key not in data:
        raise KeyError(f"Missing required key '{key}' in {context}")
    
    value = data[key]
    if value is None:
        raise ValueError(f"Value for key '{key}' in {context} cannot be None")
    
    return value

def _validate_int(value, key_name: str, context: str = "") -> int:
    """Checks whether the value is an integer.

    Since `bool` is a subclass of `int`, a simple check of `isinstance(value, int)`
    will return True for the Boolean values True and False. This function explicitly
    excludes Boolean types to avoid logical errors.

    Args:
        value: The value being checked.
        key_name (str): The name of the key associated with value, used for the error message.
        context (str, optional): A string description of the context, used to generate
            the error message. By default, an empty string.

    Returns:
        int: The original value, if it has passed validation.

    Raises:
        ValueError: If the value is not an integer or is a Boolean type.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    else:
        raise ValueError(
            f"Invalid integer value for '{key_name}' in {context}: got '{value}' (type: {type(value).__name__})"
        )

def _validate_path_exists(path_str: str, key_name: str, context: str = "", is_file: bool = True) -> pathlib.Path:
    """Checks the existence of a path in the file system.

    Converts a path string to a pathlib.Path object and checks its presence on the disk.
    Depending on the `is_file` flag, it expects either a file or a directory.

    Args:
        path_str (str): String representation of a path.
        key_name (str): The name of the key associated with the path.
        context (str, optional): A string description of the context, used to generate
            the error message. By default, an empty string.
        is_file (bool, optional): If True, it checks if the file exists.
            If False, checks if the directory exists. By default, True.

    Returns:
        pathlib.Path: The Path object corresponding to the verified path.

    Raises:
        FileNotFoundError: If `is_file=True` and this file does not exist.
        NotADirectoryError: If `is_file=False` and this directory does not exist.
    """
    p = pathlib.Path(path_str)
    
    if is_file:
        if not p.is_file():
            raise FileNotFoundError(
                f"File not found for '{key_name}' in {context}: {p.resolve()}"
            )
    else:
        if not p.is_dir():
            raise NotADirectoryError(
                f"Directory not found for '{key_name}' in {context}: {p.resolve()}"
            )
            
    return p

if not CONFIG_FILE.exists():
    raise FileNotFoundError(f"Configuration file is not found: {CONFIG_FILE}")

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    _cfg = yaml.safe_load(f)

if _cfg is None:
    raise ValueError(f"Configuration file '{CONFIG_FILE}' is empty or not contains valid YAML data")

DB_USER = str(_get_value(_cfg, "db_user", "root"))
DB_NAME = str(_get_value(_cfg, "db_name", "root"))

test_outputs_dir_str = _get_value(_cfg, "test_outputs_dir", "root")
TEST_OUTPUTS_DIR = _validate_path_exists(test_outputs_dir_str, "test_outputs_dir", "root", is_file=False)

RESULTS_DIR = TEST_OUTPUTS_DIR / "results"
DIFFS_DIR = TEST_OUTPUTS_DIR / "diffs"
LOG_DIR = TEST_OUTPUTS_DIR / "test_logs"

postgres_servers_raw = _get_value(_cfg, "postgres_servers", "root")

POSTGRES_SERVERS = {}
for server_name, server_cfg in postgres_servers_raw.items():
    context = f"postgres_servers['{server_name}']"

    host = str(_get_value(server_cfg, "host", context))
    port = _validate_int(_get_value(server_cfg, "port", context), "port", context)
    install_path = str(_get_value(server_cfg, "install_path", context))

    _validate_path_exists(install_path, "install_path", context, is_file=False)
    
    bin_path_obj = pathlib.Path(install_path) / "bin" / "psql"

    POSTGRES_SERVERS[server_name] = {
        "host": host,
        "port": port,
        "bin_path": str(bin_path_obj)
    }

tests_raw = _get_value(_cfg, "tests", "root")

TESTS = {}
for test_name, test_cfg in tests_raw.items():
    context = f"tests['{test_name}']"

    test_sql_script_path = _validate_path_exists(
        str(_get_value(test_cfg, "test_sql_script_path", context)), 
        "test_sql_script_path", context, is_file=True
    )
    
    test_expected_out_file_path = _validate_path_exists(
        str(_get_value(test_cfg, "test_expected_out_file_path", context)), 
        "test_expected_out_file_path", context, is_file=True
    )
    
    reset_database_sql_file_path = _validate_path_exists(
        str(_get_value(test_cfg, "reset_database_sql_file_path", context)), 
        "reset_database_sql_file_path", context, is_file=True
    )

    date_style = str(_get_value(test_cfg, "date_style", context))
    timezone = str(_get_value(test_cfg, "timezone", context))
    interval_style = str(_get_value(test_cfg, "interval_style", context))
    lc_time = str(_get_value(test_cfg, "lc_time", context))

    extra_float_digits = _validate_int(
        _get_value(test_cfg, "extra_float_digits", context), 
        "extra_float_digits", context
    )

    TESTS[test_name] = {
        "test_sql_script_path": str(test_sql_script_path),
        "test_expected_out_file_path": str(test_expected_out_file_path),
        "reset_database_sql_file_path": str(reset_database_sql_file_path),
        "date_style": date_style,
        "timezone": timezone,
        "interval_style": interval_style,
        "extra_float_digits": extra_float_digits,
        "lc_time": lc_time
    }

del _cfg