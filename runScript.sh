# check if Python 3.15.0 or higher is installed
P_Req='3.15.0'
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python $P_Req or newer was not found. Please install it and try again."
    exit 1
fi

P_Out=$(python3 --version 2>/dev/null)
if [[ ! $P_Out =~ ^Python\ ([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
    echo "Could not recognize the Python version. Please install Python $P_Req or newer."
    exit 1
fi

P_Major=${BASH_REMATCH[1]}
P_Minor=${BASH_REMATCH[2]}
P_Patch=${BASH_REMATCH[3]}
if (( P_Major < 3 || (P_Major == 3 && P_Minor < 15) || (P_Major == 3 && P_Minor == 15 && P_Patch < 0) )); then
    echo "$P_Out is too old. Please install Python $P_Req or newer."
    exit 1
fi
echo "$P_Out is installed"

# check if MariaDB is installed
if ! command -v mariadb >/dev/null 2>&1; then
    echo "MariaDB was not found. Please install MariaDB and try again."
    exit 1
fi

M_Out=$(mariadb --version 2>/dev/null | cut -c 1-27)
echo "$M_Out is installed"

# run update script so recent files
chmod u+x updateProject.sh
./updateProject.sh

# run server or access server

# run python scripts 