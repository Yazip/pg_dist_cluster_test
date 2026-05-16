#!/bin/bash
set -euo pipefail

error_exit() {
	echo "Error: $1" >&2
	exit 1
}

if [ $# -ne 3 ]; then
	echo "Argument count error: correct argument count is 3" >&2
	echo "Usage: $0 <base_directory> \"<version1 version2 ...>\" \"<port1 port2 ...>\"" >&2
	echo "Example: $0 . \"12 14 16\" \"5432 5433 5434\"" >&2
	echo "Example: $0 /home \"15_18 17 18_4\" \"1518 1700 1804\"" >&2
	exit 1
fi

BASE_DIR="$1"
VERSIONS_STR="$2"
PORTS_STR="$3"

if [ ! -d "$BASE_DIR" ]; then
	error_exit "This directory does not exist: $BASE_DIR"
fi

declare -a versions=()
for ver in $VERSIONS_STR; do
	if [ -z "$ver" ]; then
        	continue
    	fi
	
	if [[ ! "$ver" =~ ^[0-9_]+$ ]]; then
        	error_exit "Invalid version format: '$ver'. Only digits and underscores are allowed"
    	fi
	
	versions+=("$ver")
done

if [ ${#versions[@]} -eq 0 ]; then
	error_exit "No valid versions specified"
fi

declare -a ports=()
for port in $PORTS_STR; do
	if [ -z "$port" ]; then
        	continue
    	fi
	
	if [[ ! "$port" =~ ^[0-9]+$ ]]; then
        	error_exit "Invalid port format: '$port'. Only digits are allowed"
    	fi
	
	ports+=("$port")
done

if [ ${#ports[@]} -eq 0 ]; then
	error_exit "No valid ports specified"
fi

if [ ${#versions[@]} -ne ${#ports[@]} ]; then
	error_exit "Mismatch between number of versions (${#versions[@]}) and number of ports (${#ports[@]})"
fi

LOG_DIR="$BASE_DIR/pg_logs"

for i in "${!versions[@]}"; do
	ver="${versions[$i]}"
	port="${ports[$i]}"

	echo "PostgreSQL $ver server starting on port $port..."
	
	install_dir="$BASE_DIR/pgsql$ver"
	
	"$install_dir/bin/pg_ctl" -D "$install_dir/data" -l "$LOG_DIR/logfile$ver" -o "-p $port" start

	echo "PostgreSQL $ver is running on port $port!"
done

echo "All servers started!"
