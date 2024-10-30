# Check if the script is being sourced in bash, otherwise raise an error
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

# Check which platform is being used and source the correct cvmfs script
SOS_ANALYSIS_DIR=$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)
source /etc/os-release
if [[ "$PLATFORM_ID" == "platform:el8" ]]; then
    echo "You are using el8. It should work, otherwise, use an el9 container:"
    echo "apptainer shell -B /eos -B /afs -B /cvmfs /cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/sft/docker/alma9:latest"
    source /cvmfs/sft.cern.ch/lcg/views/dev4cuda/latest/x86_64-el8-gcc11-opt/setup.sh
elif [[ "$PLATFORM_ID" == "platform:el9" ]]; then
    source /cvmfs/sft.cern.ch/lcg/views/LCG_106_cuda/x86_64-el9-gcc11-opt/setup.sh
else
    echo "Unsupported platform: $PLATFORM_ID. You must use el8 or el9 (preferred)"
    return 1
fi

CURRENT_PWD=$(pwd)
cd $SOS_ANALYSIS_DIR/cmgrdf-prototype
# Check if the user wants to build cmgrdf
if [[ "$1" == "build" ]]; then
    make clean
    make -j 8
fi
# Set the environment variables
eval $(make env)
cd $CURRENT_PWD
