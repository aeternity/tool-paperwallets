#!/bin/sh

# generates the accounts required to run a session of the beer app
TAG='cwp' # tag for the session
NUM_ACCOUNTS=300



./republica.py gen -n $NUM_ACCOUNTS -t $TAG
./republica.py makeurls -t $TAG
./republica.py postcards -t $TAG -f $TAG
./republica.py fill -t $TAG 
./republica.py claim -t $TAG 
