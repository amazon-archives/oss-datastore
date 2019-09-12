#!/bin/bash

SITE_PACKAGES=$(pipenv --venv)/lib/python3.6/site-packages
echo "Library Location: $SITE_PACKAGES"
cd lambda
# get full path to lambda folder
DIR=$(pwd)
# delete the package.zip if it exists
if [ -e package.zip ]
then
  rm package.zip
fi
cd --

# Make sure pipenv is good to go
echo "Do fresh install to make sure everything is there"
pipenv install

cd $SITE_PACKAGES
zip -r9 $DIR/package.zip *

cd $DIR
zip -g package.zip github-data-pull.py 
cd ../
zip -gr lambda/package.zip GitHub_V3 GitHub_V4
