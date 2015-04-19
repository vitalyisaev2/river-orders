#!/bin/bash

header="id;river_full_name;river_dest;side;dest_from_end;length;watershed_area;ten_km_trib_amount;ten_km_trib_sum_len;lakes_amount;lakes_sum_area;table3_id;;;;;"

sed -i '1i'$header $1
sed -i 's/*//g' $1
sed -i 's/вдхр\ /вдхр.\ /g' $1
sed -i 's/оз\ /оз.\ /g' $1
