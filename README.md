# river-orders
Simple tool for building river network graph from data published in USSR Surface water resources ("Гидрологическая изученность").

#### Installation and usage
Early pre-alpha. Linux only. Honestly, there's nothing for you to see yet. But if you really want, you should [install](https://docs.docker.com/installation/) docker first. Next you need to
```sh
$ git clone git@github.com:vitalyisaev2/river-orders.git
$ cd river-orders
$ docker build --tag=river-orders ./docker
$ docker run --privileged -it --rm -v `pwd`:/home/hydrologist/project:ro river-orders bash
``` 
When you're inside the container, start ipython session:
```sh
hydrologist@35922fe8329b:~/project$ ipython
In [1]: %run build_river_network.py data/example.long.csv -f data/example.long.fixture
```

