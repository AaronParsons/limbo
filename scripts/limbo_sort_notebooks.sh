#! /usr/bin/bash

export DATAPATH=/home/obs/data

cd ${DATAPATH}/notebook

for f in `ls *.dat.ipynb`
do
    fdat=`echo Spectra_20230321152750.dat.ipynb | sed "s/.ipynb//"`
    if test -f "${DATAPATH}/save/${fdat}"; then
	    echo Moving ${f} to ${DATAPATH}/notebook/save
	    mv ${f} ${DATAPATH}/notebook/save
    elif test -f "${DATAPATH}/remove/${fdat}"; then
        echo Moving ${f} to ${DATAPATH}/notebook/remove
	    mv ${f} ${DATAPATH}/notebook/remove
    else
        echo Could not find ${fdat}
    fi
done
