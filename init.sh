#!/bin/bash

function err() {

  echo "ERR: $* exiting"
  exit 1

}

## main ##

# global variables
CMD="${0##*/}"
BIN_DIR="${0%/*}"
cd $BIN_DIR

VIRTUALENV_NAME="venv"

pip show virtualenv >> /dev/null 2>&1
if [ $? -ne 0 ]; then
  pip install virtualenv >>/dev/null 2>&1 || sudo pip install virtualenv >>/dev/null 2>&1

  [ $? -ne 0 ] && err "Unable to install virtualenv.  Please install by hand then run this again"
fi

# Check to see if virtualenv exists
if [ -d "${VIRTUALENV_NAME}" ] && [ -e "${VIRTUALENV_NAME}/bin/activate" ]; then
  [ "${VIRTUAL_ENV##*/}" != "${VIRTUAL_ENV}" ] && . "${VIRTUALENV_NAME}/bin/activate"

  [ -z "${VIRTUALENV_NAME}" ] && err "Unable to switch to ${VIRTUALENV_NAME}.  Please consult python virtualenv documentation"


else
  # virtualenv is not configured yet
  virtualenv ${VIRTUALENV_NAME}

  . "${VIRTUALENV_NAME}/bin/activate"
fi

pip install -r requirements.txt

fab build:centos6
fab build:centos7

[ -e builds/rpms/centos/6/x86_64/git-1.8.3*.rpm ] || fab build_git18
