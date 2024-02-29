#! /usr/bin/bash

export DATAPATH=/home/obs/data
export REMOVE_DIR=/mnt/data03

dates=($(python /home/obs/limbo/scripts/limbo_get_data_dates.py | tr -d '[],'))
digits=(${dates[@]//\'/})

cd ${DATAPATH}/notebook

for d in "${digits[@]}"
do
    for f in ${d}
    do
        fdat=`echo ${f} | sed "s/.ipynb//"`
	if test -f "${DATAPATH}/save/${fdat}"; then
            echo Moving ${f} to ${DATAPATH}/notebook/save
            mv ${f} ${DATAPATH}/notebook/save
        elif test -f "${REMOVE_DIR}/${fdat}"; then
            echo Moving ${f} to ${DATAPATH}/notebook/remove
            mv ${f} ${DATAPATH}/notebook/remove
        else
            echo Could not find ${fdat}
        fi
    done
done
