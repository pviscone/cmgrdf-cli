# Check if the script is being sourced in bash, otherwise raise an error
export CMGRDF_CLI=$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)

CURRENT_SHELL=$(ps -p $$ -o comm=)
if [[ "$CURRENT_SHELL" == "zsh" ]]; then
    echo "ZSH can't source the cvmfs scripts. You must source it in bash and then return to zsh" >&2
    return 1
fi

# Check if the script is being sourced in bash, otherwise raise an error
if [[ ${BASH_SOURCE[0]} == $0 ]]; then
   echo "You must source this script, not execute it. Run 'source setup.sh'" >&2
   exit 1
fi

CURRENT_PWD=$(pwd)
cd $CMGRDF_CLI/cmgrdf-prototype
# Check if the user wants to build cmgrdf
if [[ "$1" == "build" ]]; then
    make clean
    make -j 8
fi

# Set the environment variables
eval $(make env)
if [[ "$1" == "build" ]]; then
    python3 -m venv "$CMGRDF_CLI/.venv"
    source "$CMGRDF_CLI/.venv/bin/activate"
    pip install -r $CMGRDF_CLI/requirements.txt
    pip install XRootD uproot
else
    source "$CMGRDF_CLI/.venv/bin/activate"
fi

export PATH=$CMGRDF_CLI/.venv/bin:$CMGRDF_CLI:$CMGRDF_CLI/scripts:$CMGRDF_CLI/bin:$PATH
cd $CURRENT_PWD
