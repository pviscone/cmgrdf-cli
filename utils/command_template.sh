#!/bin/bash

zlog="$(dirname "$(realpath "$0")")"

if [[ -z "$CMGRDF" ]] && [ ! -d $zlog/cmgrdf-prototype ]; then
    echo "CMGRDF is not set, I am cloning it for you, lazy human."
    read -p "Are you sure (it's a big repo to clone again) (y/n)?" CONT
    if [ "$CONT" = "y" ]; then
        git clone --recursive https://gitlab.cern.ch/cms-new-cmgtools/cmgrdf-prototype.git
        cd $zlog/cmgrdf-prototype
        if [ -f cmgrdf_commit.txt ]; then
            read -r saved_commit < cmgrdf_commit.txt
            git checkout --recurse-submodules $saved_commit
        else
            echo "CMGRDF commit hash not found, cloning last commit of dpee branch"
            git checkout --recurse-submodules dpee
        fi
        cd $zlog
        echo "CMGRDF cloned"
        echo "Starting to build CMGRDF"
        source $zlog/setup.sh build
    else
        exit 1
    fi
fi

cd $CMGRDF
commit_hash=`git describe --match=NeVeRmAtCh --always --abbrev=40 --dirty`
current_diff=$(git diff)
cd $zlog
#This block of code just warn you if you are using a different version of CMGRDF than the one you used to run tha analysis
if [ -f cmgrdf_commit.txt ]; then
    read -r saved_commit < cmgrdf_commit.txt
    if [ "$commit_hash" = "$saved_commit" ]; then
        if [[ "$commit_hash" == *-dirty ]]; then
            saved_diff=$(tail -n +2 cmgrdf_commit.txt)
            if [ "$saved_diff" != "$current_diff" ]; then
                echo "Warning! CMGRDF is/was in a dirty state and diffs do not match."
            fi
        fi
    else
        echo "Warning! CMGRDF commit hashes do not match."
    fi
fi

