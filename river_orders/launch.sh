#!/bin/bash

docker run --privileged -it --rm -v `pwd`:/home/vitaly/project:ro river_orders bash
