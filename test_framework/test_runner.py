import pathlib
import re

import psql_runner
import parser

def reset_database(cfg: dict, path_to_script: str):
    """Reset the database to a clean state for testing.

    This ensures that each test starts with a consistent state.

    Args:
        cfg (dict): Server configuration with keys 'host', 'port', 'bin_path'.
        path_to_script (str): Path to SQL-script which contains commands to reset database.
    """
    sql_parts = []

    with open(path_to_script, 'r', encoding='utf-8') as f:
        for line in f:
            stripped_line = line.strip()
            
            if stripped_line:
                sql_parts.append(stripped_line)

    sql = "\n".join(sql_parts)
    psql_runner.run_psql_capture(sql, cfg)

def run_test(test_cfg: dict, cfg_a: dict, cfg_b: dict) -> tuple[str, str]:
    """Run a single SQL test file against two PostgreSQL servers and capture outputs.

    This function:
        - Resets both databases
        - Parses the test file into commands
        - Executes commands on both servers
        - Captures output for comparison

    Args:
        test_cfg (dict): Configuration of the test.
        cfg_a (dict): Configuration of the first PostgreSQL server.
        cfg_b (dict): Configuration of the second PostgreSQL server.

    Returns:
        tuple[str, str]: Captured outputs from server A and server B.
    """
    output_a = []
    output_b = []

    reset_database(cfg_a, test_cfg["reset_database_sql_file_path"])
    reset_database(cfg_b, test_cfg["reset_database_sql_file_path"])

    commands = parser.parse_test_file(pathlib.Path(test_cfg["test_sql_script_path"]))

    date_style = test_cfg["date_style"]
    timezone = test_cfg["timezone"]
    interval_style = test_cfg["interval_style"]
    extra_float_digits = test_cfg["extra_float_digits"]
    lc_time = test_cfg["lc_time"]

    psql_a = psql_runner.start_psql(cfg_a)
    # This is necessary for proper output to the .out file.
    psql_runner.send_cmd_and_capture(psql_a, f"SET DateStyle = '{date_style}';")
    psql_runner.send_cmd_and_capture(psql_a, f"SET TimeZone = '{timezone}';")
    psql_runner.send_cmd_and_capture(psql_a, f"SET IntervalStyle = '{interval_style}';")
    psql_runner.send_cmd_and_capture(psql_a, f"SET extra_float_digits = {extra_float_digits};")
    psql_runner.send_cmd_and_capture(psql_a, f"SET lc_time = '{lc_time}';")
    
    psql_b = psql_runner.start_psql(cfg_b)
    psql_runner.send_cmd_and_capture(psql_b, f"SET DateStyle = '{date_style}';")
    psql_runner.send_cmd_and_capture(psql_b, f"SET TimeZone = '{timezone}';")
    psql_runner.send_cmd_and_capture(psql_b, f"SET IntervalStyle = '{interval_style}';")
    psql_runner.send_cmd_and_capture(psql_b, f"SET extra_float_digits = {extra_float_digits};")
    psql_runner.send_cmd_and_capture(psql_b, f"SET lc_time = '{lc_time}';")

    try:
        for cmd in commands:
            if not cmd.strip():
                continue
            
            cmd_stripped = cmd.lstrip()

            # PL/pgsql
            if re.search(r"\$\w*\$", cmd) is not None:
                try:
                    # Substitute it for the port of the remote server in a pair
                    patched_cmd = re.sub(
                        r"current_setting\(\s*['\"]port['\"]\s*\)",
                        str(cfg_b["port"]),
                        cmd,
                        flags=re.IGNORECASE
                    )
                    
                    output_a.append(patched_cmd.rstrip() + "\n")
                    
                    out_a = psql_runner.run_single_plpgsql(patched_cmd, cfg_a)
                except RuntimeError as e:
                    out_a = str(e)

                try:
                    patched_cmd = re.sub(
                        r"current_setting\(\s*['\"]port['\"]\s*\)",
                        str(cfg_a["port"]),
                        cmd,
                        flags=re.IGNORECASE
                    )
                    
                    output_b.append(patched_cmd.rstrip() + "\n")
                    
                    out_b = psql_runner.run_single_plpgsql(patched_cmd, cfg_b)
                except RuntimeError as e:
                    out_b = str(e)
                
                # Removing unnecessary output (the path to the temp file and the error code)
                if ('\n' in out_a):
                    out_a_lines = out_a.split('\n')
                    for i in range(len(out_a_lines)):
                        out_a_lines[i] = re.sub(r'^.+:\d+:\s+', '', out_a_lines[i])
                    out_a = '\n'.join(out_a_lines)
                if ('\n' in out_b):
                    out_b_lines = out_b.split('\n')
                    for i in range(len(out_b_lines)):
                        out_b_lines[i] = re.sub(r'^.+:\d+:\s+', '', out_b_lines[i])
                    out_b = '\n'.join(out_b_lines)
                
                output_a.append(out_a)
                output_b.append(out_b)
                continue
            
            # SQL, psql metacommands, single-line and multiline comments
            else:
                if (cmd.lower().startswith("copy")) and ("from stdin" in cmd.lower()): # For correct output to .out file
                    output_a.append((cmd.split("\n")[0] + "\n").rstrip() + "\n")
                    output_b.append((cmd.split("\n")[0] + "\n").rstrip() + "\n")
                else:
                    output_a.append(cmd.rstrip() + "\n")
                    output_b.append(cmd.rstrip() + "\n")
                
                out_a = psql_runner.send_cmd_and_capture(psql_a, cmd)
                out_a = out_a.replace("__CMD_END__\n", "") # Removing the marker for the end of the command output from the output to the .out file
                output_a.append(out_a)
                
                out_b = psql_runner.send_cmd_and_capture(psql_b, cmd)
                out_b = out_b.replace("__CMD_END__\n", "")
                output_b.append(out_b)
    finally: # Guaranteed closure of psql sessions
        try:
            psql_a.stdin.close()
            psql_b.stdin.close()
        except Exception:
            pass
        try:
            psql_a.communicate()
            psql_b.communicate()
        except Exception:
            pass

    return "".join(output_a), "".join(output_b)