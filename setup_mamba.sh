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

warn_activate(){
    echo Remember to activate the enviroment first 
    echo "          micromamba activate $CMGRDF_CLI/.venv"
    echo ""
    echo "" 
}


CURRENT_PWD=$(pwd)
cd $CMGRDF_CLI/cmgrdf-prototype
# Check if the user wants to build cmgrdf
if [[ "$1" == "create" ]]; then
    micromamba env create -f $CMGRDF_CLI/environment.yml -p $CMGRDF_CLI/.venv
elif [[ "$1" == "build" ]]; then
    warn_activate
    make clean
    make -j 8
else 
    warn_activate
fi


# Set the environment variables
eval $(make env)

export PATH=$CMGRDF_CLI:$CMGRDF_CLI/scripts:$CMGRDF_CLI/bin:$PATH
cd $CURRENT_PWD
