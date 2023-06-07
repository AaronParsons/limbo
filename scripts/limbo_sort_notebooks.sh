#! /usr/bin/bash

export DATAPATH=/home/obs/data
export REMOVE_DIR=/mnt/data03

cd ${DATAPATH}/notebook

for f in `ls *.dat.ipynb`
do
    fdat=`echo ${f} | sed "s/.ipynb//"`
    if test -f "${DATAPATH}/save/${fdat}"; then
        echo Moving ${f} to ${DATAPATH}/notebook/save
        mv ${f} ${DATAPATH}/notebook/save
#     elif test -f "${DATAPATH}/remove/${fdat}"; then
    elif test -f "${REMOVE_DIR}/${fdat}"; then
        echo Moving ${f} to ${DATAPATH}/notebook/remove
        mv ${f} ${DATAPATH}/notebook/remove
    else
        echo Could not find ${fdat}
    fi
done
