#This block of code just warn you if you are using a different version of CMGRDF than the one you used to run tha analysis
pwd=$(pwd)
cd $CMGRDF
commit_hash=`git describe --match=NeVeRmAtCh --always --abbrev=40 --dirty`
current_diff=$(git diff)
cd $pwd

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

