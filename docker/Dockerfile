FROM ubuntu:latest

MAINTAINER Vitaly Isaev <vitalyisaev2@gmail.com>

ENV DEBIAN_FRONTEND noninteractive

ENV REFRESHED_AT 12.4.2015

RUN sed -i.bak 's/http:\/\/archive.ubuntu.com\/ubuntu\//mirror:\/\/mirrors.ubuntu.com\/mirrors.txt\//g' /etc/apt/sources.list
RUN apt-get -y update

RUN apt-get -y install python3-pip
RUN apt-get -y install python3-pandas
RUN apt-get -y install python3-yaml
RUN apt-get -y install graphviz
RUN apt-get -y install imagemagick

RUN pip3 install networkx 
RUN pip3 install ipython 
RUN pip3 install ipdb 
RUN pip3 install graphviz

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8

RUN useradd -m hydrologist
RUN echo 'hydrologist:hydrologist' | chpasswd
VOLUME ["/home/hydrologist/project"]
WORKDIR /home/hydrologist/project

USER hydrologist
#USER root
