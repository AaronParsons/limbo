#! /usr/bin/bash

export DATAPATH=/home/obs/data

cd ${DATAPATH}/save

for f in `ls *.dat`
do
	echo Moving ${f}.ipynb to ${DATAPATH}/notebook/save
	mv ../notebook/${f}.ipynb ../notebook/save 
done

cd ${DATAPATH}/remove

for f in `ls *.dat`
do
	echo Moving ${f}.ipynb to ${DATAPATH}/notebook/remove
	mv ../notebook/${f}.ipynb ../notebook/remove
done
