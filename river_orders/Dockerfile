FROM ubuntu:latest

MAINTAINER Vitaly Isaev <vitalyisaev2@gmail.com>

ENV DEBIAN_FRONTEND noninteractive

RUN sed -i.bak 's/http:\/\/archive.ubuntu.com\/ubuntu\//mirror:\/\/mirrors.ubuntu.com\/mirrors.txt\//g' /etc/apt/sources.list
RUN apt-get -y update

RUN apt-get -y install python3-pip
RUN apt-get -y install python3-pandas

RUN pip3 install networkx 
RUN pip3 install ipython 

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8

RUN useradd -m vitaly
RUN echo 'vitaly:vitaly' | chpasswd
VOLUME ["/home/vitaly/project"]
WORKDIR /home/vitaly/project

USER vitaly
