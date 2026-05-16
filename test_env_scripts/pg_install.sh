#!/bin/bash
set -euo pipefail

error_exit() {
	echo "Error: $1" >&2
	exit 1
}

if [ $# -ne 3 ]; then
	echo "Argument count error: correct argument count is 3" >&2
	echo "Usage: $0 <base_directory> \"<version1 version2 ...>\" <role>" >&2
	echo "Example: $0 . \"12 14 16\" john" >&2
	echo "Example: $0 /home \"15_18 17 18_4\" tom" >&2
	exit 1
fi

BASE_DIR="$1"
VERSIONS_STR="$2"
ROLE="$3"

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

if [[ ! "$ROLE" =~ ^[a-zA-Z0-9_-]+$ ]]; then
	error_exit "Invalid role format: '$ROLE'. Only letters, digits, underscores, and hyphens are allowed"
fi

LOG_DIR="$BASE_DIR/pg_logs"
mkdir -p "$LOG_DIR"

for ver in "${versions[@]}"; do
	echo "PostgreSQL $ver installation..."
	
	if [[ "$ver" == *"_"* ]]; then
        	MAJOR="${ver%%_*}"
        	MINOR="${ver##*_}"
    	else
        	MAJOR="$ver"
        	MINOR="0"
    	fi
	
    	src_dir="$BASE_DIR/postgresql_$ver"
    	install_dir="$BASE_DIR/pgsql$ver"
    	data_dir="$install_dir/data"
    	log_file="$LOG_DIR/logfile$ver"
    	port=$(( 5432 + (MAJOR * 100) + MINOR ))
	
	cd "$src_dir"
    	CFLAGS="-Og" ./configure \
		--prefix="$install_dir" \
        	--with-pgport="$port" \
        	--enable-cassert \
        	--enable-debug \
        	--without-icu
	cd "$BASE_DIR"
	
    	make -C "$src_dir" -j$(nproc) world-bin

    	make -C "$src_dir" install-world-bin

	mkdir -p "$data_dir"

	"$install_dir/bin/initdb" --no-sync -U postgres -k -D "$data_dir"

	"$install_dir/bin/pg_ctl" -D "$data_dir" -l "$log_file" -o "-p $port" start

	echo "PostgreSQL $ver is running on port $port!"

	"$install_dir/bin/psql" -U postgres -p "$port" -h localhost -c "CREATE ROLE \"$ROLE\" WITH LOGIN SUPERUSER;" || true

done

echo "All versions of PostgreSQL are successfully installed and running!"
