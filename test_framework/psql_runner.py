import os
import subprocess
import tempfile

import config

def start_psql(cfg: dict) -> subprocess.Popen:
    """Start a psql subprocess with the given server configuration.

    Args:
        cfg (dict): Server configuration dictionary with keys:
            'host', 'port', 'bin_path'.

    Returns:
        subprocess.Popen: Running psql subprocess with stdin/stdout pipes.
    """
    env = os.environ.copy() # Copying the current environment variables
    env["PGUSER"] = config.DB_USER

    return subprocess.Popen(
        [
            cfg["bin_path"],
            "-X", "-q",
            "-h", cfg["host"],
            "-p", str(cfg["port"]),
            "-U", config.DB_USER,
            "-d", config.DB_NAME,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # Errors from stderr in stdout
        text=True,
        bufsize=1, # Line buffering
        env=env,
    )

def run_single_plpgsql(cmd: str, cfg: dict) -> str:
    """Execute a single PL/pgSQL block using a temporary SQL file.

    Args:
        cmd (str): PL/pgSQL block to execute.
        cfg (dict): Server configuration.

    Returns:
        str: Captured stdout from execution.

    Raises:
        RuntimeError: If execution fails.
    """
    env = os.environ.copy()
    env["PGUSER"] = config.DB_USER
    
    with tempfile.NamedTemporaryFile("w", suffix=".sql") as f:
        f.write(cmd + "\n")
        f.flush()

        proc = subprocess.run(
            [
                cfg["bin_path"],
                "-X", "-q",
                "-h", cfg["host"],
                "-p", str(cfg["port"]),
                "-U", config.DB_USER,
                "-d", config.DB_NAME,
                "-f", f.name
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )

        if proc.returncode != 0:
            raise RuntimeError(f"Error during execution PL/pgSQL block:\n{proc.stdout}")

        return proc.stdout

def run_psql_capture(cmd_text: str, cfg: dict) -> str:
    """Run SQL command via psql and capture output.

    Args:
        cmd_text (str): SQL command text.
        cfg (dict): Server configuration.

    Returns:
        str: stdout from psql execution.

    Raises:
        RuntimeError: If psql exits with a non-zero code.
    """
    proc = subprocess.Popen(
        [
            cfg["bin_path"],
            "-X",
            "-q",
            "-h", cfg["host"],
            "-p", str(cfg["port"]),
            "-U", config.DB_USER,
            "-d", config.DB_NAME,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    out, _ = proc.communicate(cmd_text + "\n")
    if proc.returncode != 0:
        raise RuntimeError(out)

    return out

def is_only_comments_or_whitespace(cmd: str) -> bool:
    """Check if a SQL command contains only comments or whitespace.

    Args:
        cmd (str): SQL command.

    Returns:
        bool: True if the command has no executable SQL, False otherwise.
    """
    in_multiline_comment = False
    # Processing the command line by line
    for line in cmd.splitlines():
        stripped = line.strip()
        # Skipping empty strings
        if not stripped:
            continue
        # Skipping single-line comments
        if stripped.startswith("--"):
            continue
        # Skipping multiline comments
        if stripped.startswith("/*"):
            in_multiline_comment = True
            if "*/" in stripped:
                in_multiline_comment = False
                continue
            continue
        if in_multiline_comment:
            if "*/" in stripped:
                in_multiline_comment = False
                continue
            continue
        # If an executable SQL command is found
        return False
    # If no executable SQL commands are found
    return True

END_MARKER = "__CMD_END__"
"""str: Marker used to identify the end of command output."""

def send_cmd_and_capture(psql_proc: subprocess.Popen, cmd: str) -> str:
    """Send a command to a running psql subprocess and capture output until END_MARKER.

    Args:
        psql_proc (subprocess.Popen): Active psql subprocess.
        cmd (str): SQL or psql command.

    Returns:
        str: Captured output.

    Raises:
        RuntimeError: If psql terminates unexpectedly.
    """
    # Also send such commands to stdin, so as not to disrupt the output to the .out file (because they should also be present there)
    # They have no output, so we return an empty string
    if is_only_comments_or_whitespace(cmd):
        psql_proc.stdin.write(cmd + "\n")
        psql_proc.stdin.flush()
        return ""

    psql_proc.stdin.write(cmd + "\n")
    psql_proc.stdin.write(f"\\echo {END_MARKER}\n") # This is necessary in order to determine the end of the output of this command
    psql_proc.stdin.flush()

    lines = []
    # Read the output line by line until we find the END_MARKER (if we haven't found it and stdout is already closed, we raise an exception because this is unexpected behavior)
    while True:
        line = psql_proc.stdout.readline()
        if not line:
            rc = psql_proc.poll()
            raise RuntimeError(f"PSQL ended unexpectedly. Code: {rc}\nOutput:\n{''.join(lines)}")
        lines.append(line)
        if END_MARKER in line:
            break
    return "".join(lines) # Return the entire output