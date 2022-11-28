#! /bin/bash

# This script allows you to easily manage
# RNApdbee Adapters docker image and docker container
# You use this script at your own risk
# Please always analyze the code of bash scripts first

image="rnapdbee-adapters-image" # Docker image name
container="rnapdbee-adapters-container" # Docker container name
target="server" # Target in 'docker build' command
port="8000:80" # Port mapping in 'docker create' command

# Colors for echo command
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NORMAL='\033[0m'

function show_help {

cat << EOF 
Usage: $0 [OPTION]...
Manage docker image $image and docker container $container
WARNING: you use this script at your own risk. Please analyze the code first.

Short options are available as well as long options. The order doesn't matter.
Joined options (for example -tcr) ARE NOT ALLOWED.
  -h, --help        show this help
  -c, --create      create image $image and container $container
  -t, --test        test docker container $container
  -r, --run         run docker container $container
EOF

}

# Declare associative array containing user options
declare -A stage=( [test]=false [create]=false [run]=false )

# No options passed to script -> show help
if [ "$#" -eq 0 ] ; then
    show_help
    exit 0
fi

# Parse user options
for option in "$@" ; do
    case "$option" in
        '-t' | '--test') stage[test]=true ;;
        '-c' | '--create') stage[create]=true ;;
        '-r' | '--run') stage[run]=true ;;
        '-h' | '--help') show_help ; exit 0 ;;
        *) printf "$0: unrecognized option '$option' \n\n" ; show_help ; exit 0 ;;
    esac
done

# Stage create
# ------------
# WARNING: Force remove container $container: docker container rm -f $container
# WARNING: Force prune of all dangling images: docker image prune -f 
# WARNING: Force prune of all dangling cache: docker builder prune -f 
if [ ${stage[create]} = true ] ; then
    DOCKER_BUILDKIT=1 docker build --target $target -t $image . && \
    docker container rm -f $container > /dev/null && \
    docker create --name $container -p $port $image && \
    docker image prune -f > /dev/null && \
    docker builder prune -f > /dev/null && \
    echo -e "${GREEN}### CREATE OK ###${NORMAL}" || { echo -e "${RED}### CREATE FAILED ###${NORMAL}" ; exit 1 ; }
fi

# Stage test
# ------------
if [ ${stage[test]} = true ] ; then
    docker start $container && \
    docker cp tests/ $container:rnapdbee-adapters/src/ && \
    docker cp pylintrc $container:/ && \
    docker cp test_requirements.txt $container:/ && \
    echo -e "${BLUE}Installing test_requirements.txt...${NORMAL}" && \
    docker exec -t $container bin/bash -c "pip3 install -r test_requirements.txt" > /dev/null && \
    docker exec -t $container bin/bash -c "pylint --rcfile pylintrc rnapdbee-adapters/src/adapters" && \
    docker exec -t $container bin/bash -c "cd ./rnapdbee-adapters/src/tests && pytest -v --cov='adapters'" && \
    docker stop $container && \
    echo -e "${GREEN}### TEST OK ###${NORMAL}" || { echo -e "${RED}### TEST FAILED ###${NORMAL}" ; exit 1 ; }
fi

# Stage run
# ------------
if [ ${stage[run]} = true ] ; then
    docker start -a -i $container || { echo -e "${RED}### RUN FAILED ###${NORMAL}" ; exit 1 ; }
fi
