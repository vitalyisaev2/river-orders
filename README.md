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
When you're inside the container, start the session:
```sh
$ python3 build_river_network.py data/v15.csv --fixture data/v15.fixtures.yml --node "Обь 15-3_1" --dump
```

#### Examples
The Ob river bassin:
![](http://s019.radikal.ru/i600/1504/6b/be24302c3f2a.png)
![](http://s56.radikal.ru/i151/1504/3c/c652cf2498b3.jpg)

