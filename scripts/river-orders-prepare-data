#!/bin/bash

# insert header
header="id;river_full_name;river_dest;side;dest_from_end;length;watershed_area;ten_km_trib_amount;ten_km_trib_sum_len;lakes_amount;lakes_sum_area;table3_id;volume;;;;"
sed -i '1i'$header $1

# replace all asterix
sed -i 's/*//g' $1

# fix abbreviations
sed -i 's/вдхр\ /вдхр.\ /g' $1
sed -i 's/оз\ /оз.\ /g' $1

# trailing spaces
sed -i 's/без\ названия\ ;/без\ названия;/g' $1
sed -i 's/»\ ;/»;/g' $1

# "the same" fix
sed -i 's/То\ же/»/g' $1

# Delete spaces between numbers
sed -i 's/\(\d\+\)\ \(\d\+\)/\1\2/g' $1

