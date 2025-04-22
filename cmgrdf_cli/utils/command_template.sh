#!/bin/bash

zlog="$(dirname "$(realpath "$0")")"

if [[ -z "$CMGRDF_CLI" ]] && [ ! -d $zlog/cmgrdf-cli ]; then
    echo "cmgrd-cli is not set, I am cloning it for you, lazy human."
    read -p "Are you sure (it's a big repo to clone again) (y/n)?" CONT
    if [ "$CONT" = "y" ]; then
        git clone --recursive https://github.com/pviscone/cmgrdf-cli.git
        cd $zlog/cmgrdf-cli
        if [ -f cmgrdf_cli_commit.txt ]; then
            read -r saved_commit < cmgrdf_cli_commit.txt
            git checkout --recurse-submodules $saved_commit
        else
            echo "cmgrdf-cli commit hash not found, cloning last commit of master branch"
            git checkout --recurse-submodules master
        fi
        cd $zlog
        echo "cmgrdf-cli cloned"
        echo "Starting to build cmgrdf-cli"
        source $zlog/cmgrdf-cli/setup.sh build
    else
        exit 1
    fi
fi

cd $CMGRDF_CLI
commit_hash=`git describe --match=NeVeRmAtCh --always --abbrev=40 --dirty`
current_diff=$(git diff)
cd $zlog
#This block of code just warn you if you are using a different version of cmgrdf-cli than the one you used to run tha analysis
if [ -f cmgrdf_cli_commit.txt ]; then
    read -r saved_commit < cmgrdf_cli_commit.txt
    if [ "$commit_hash" = "$saved_commit" ]; then
        if [[ "$commit_hash" == *-dirty ]]; then
            saved_diff=$(tail -n +2 cmgrdf_cli_commit.txt)
            if [ "$saved_diff" != "$current_diff" ]; then
                echo "Warning! cmgrdf_cli is/was in a dirty state and diffs do not match."
            fi
        fi
    else
        echo "Warning! cmgrdf_cli commit hashes do not match."
    fi
fi

