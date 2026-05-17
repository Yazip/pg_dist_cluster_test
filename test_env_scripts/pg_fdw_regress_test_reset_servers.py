#!/usr/bin/env python3
import subprocess
import argparse
import sys
import os

DB_USER = "postgres"
DB_NAME = "postgres"

FDW_SERVERS = (
    "loopback",
    "loopback2",
    "loopback3",
    "loopback_nopw",
    "testserver1",
)

SCHEMAS_TO_DROP = (
    "S 1",
    "import_source",
    "import_dest1",
    "import_dest2",
    "import_dest3",
    "import_dest4",
    "import_dest5",
)

def validate_inputs(names, ports, paths):
    errors = []

    for path in paths:
        if not os.path.exists(path):
            errors.append(f"Path does not exist: {path}")

    for port in ports:
        if not port.isdigit():
            errors.append(f"Port contains non-digit characters: {port}")

    if errors:
        print("[ERROR] Input validation failed:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

def run_psql(sql: str, cfg: dict):
    print(f"\n[INFO] Executing on the server 127.0.0.1:{cfg['port']}")
    try:
        proc = subprocess.run(
            [
                cfg["psql"],
                "-X",
                "-q",
                "-v", "ON_ERROR_STOP=1",
                "-h", "127.0.0.1",
                "-p", str(cfg["port"]),
                "-U", DB_USER,
                "-d", DB_NAME,
            ],
            input=sql,
            text=True,
            capture_output=True,
            timeout=60
        )

        if proc.returncode != 0:
            print(f"[ERROR] Server 127.0.0.1:{cfg['port']} returned an error:")
            print(proc.stderr)
        else:
            print(f"[OK] Server 127.0.0.1:{cfg['port']} cleared successfully")
            print(proc.stdout)

    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Server 127.0.0.1:{cfg['port']} didn't respond in 60 seconds")

def reset_server(cfg: dict):
    sql_commands = []

    for schema in SCHEMAS_TO_DROP:
        sql_commands.append(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE;')

    for srv in FDW_SERVERS:
        sql_commands.append(f"DROP SERVER IF EXISTS {srv} CASCADE;")

    sql_commands.append("DROP EXTENSION IF EXISTS postgres_fdw CASCADE;")

    sql_commands.append("DROP SCHEMA IF EXISTS public CASCADE;")
    sql_commands.append("CREATE SCHEMA public;")
    sql_commands.append("GRANT ALL ON SCHEMA public TO postgres;")

    sql_script = "\n".join(sql_commands)

    run_psql(sql_script, cfg)

def parse_arguments():
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        '--names', 
        nargs='+', 
        required=True, 
        help="List of server names (e.g., 12-1 12-2 14_23-1 server1)"
    )
    parser.add_argument(
        '--ports', 
        nargs='+', 
        required=True, 
        help="List of ports corresponding to the server names (e.g., 5432 6855 5433)"
    )
    parser.add_argument(
        '--paths', 
        nargs='+', 
        required=True, 
        help="List of paths to psql binary corresponding to the server names (e.g., /path/to/psql12 /path/to/psql13)"
    )
    
    args = parser.parse_args()
    
    if not (len(args.names) == len(args.ports) == len(args.paths)):
        print("[ERROR] The number of names, ports, and paths must be equal")
        print(f"Names count: {len(args.names)}")
        print(f"Ports count: {len(args.ports)}")
        print(f"Paths count: {len(args.paths)}")
        sys.exit(1)
    
    validate_inputs(args.names, args.ports, args.paths)
    
    return args

if __name__ == "__main__":
    args = parse_arguments()
    
    POSTGRES_SERVERS = {}
    for i in range(len(args.names)):
        name = args.names[i]
        port = args.ports[i]
        path = args.paths[i]
            
        POSTGRES_SERVERS[name] = {
            "port": port,
            "psql": path
        }

    for name, cfg in POSTGRES_SERVERS.items():
        print(f"\nClearing the server PostgreSQL {name}")
        reset_server(cfg)

    print("\nAll servers are cleared")
