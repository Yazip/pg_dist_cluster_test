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
	mkdir -p "$BASE_DIR" || error_exit "Failed to create directory: $BASE_DIR"
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
	src_dir="$BASE_DIR/postgresql_$ver"
    
	if [ -d "$src_dir" ]; then
		echo "Skipping version $ver: directory already exists ($src_dir)"
        	continue
	fi
    
	if [[ "$ver" == *"_"* ]]; then
        	BRANCH_NAME="REL_${ver}"
	else
        	BRANCH_NAME="REL_${ver}_STABLE"
	fi
    
	echo "Cloning PostgreSQL version $ver (branch: $BRANCH_NAME) into $src_dir..."
    
	git clone --single-branch --depth 1 --branch "$BRANCH_NAME" \
        	https://git.postgresql.org/git/postgresql.git "$src_dir"
done

echo "All repositories of all specified versions of PostgreSQL are successfully cloned!"
