#!/bin/bash
set -euo pipefail

error_exit() {
	echo "Error: $1" >&2
	exit 1
}

if [ $# -ne 2 ]; then
	echo "Argument count error: correct argument count is 2" >&2
	echo "Usage: $0 <base_directory> \"<version1 version2 ...>\"" >&2
	echo "Example: $0 . \"12 14 16\"" >&2
	echo "Example: $0 /home \"15_18 17 18_4\"" >&2
	exit 1
fi

BASE_DIR="$1"
VERSIONS_STR="$2"

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

for ver in "${versions[@]}"; do
	echo "PostgreSQL $ver server stopping..."
	
	install_dir="$BASE_DIR/pgsql$ver"
	
	if [ -f "$install_dir/data/postmaster.pid" ]; then
		"$install_dir/bin/pg_ctl" -D "$install_dir/data" stop -m fast
	fi
done

echo "All servers stopped!"
