#!/bin/bash
#### Runner script to start Dask workers
## Arguments
##    1)  the file to source to setup the environment
##    2)  the scheduler address
##    3+) any argumemnts to dask worker
##
ENVFILE=$1
shift
echo "At $(date), starting"
source $ENVFILE
echo "At $(date), initialized the env"
while true; do
    echo "Connecting to $*" 
    dask worker $* 
done
