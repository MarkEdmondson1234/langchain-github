#!/bin/bash

# Get the absolute path of the read_repo_wrapper.sh script
script_path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/$(basename "${BASH_SOURCE[0]}")"
script_path="$(readlink -f "$script_path" 2> /dev/null || greadlink -f "$script_path")"

# Get the script_dir from the script_path
script_dir="$(dirname "$script_path")"

# Call the read_repo.py script with the given arguments
"$script_dir/read_repo.py" "$@"
