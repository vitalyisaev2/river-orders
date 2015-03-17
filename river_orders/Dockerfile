FROM fedora:latest

MAINTAINER Vitaly Isaev <vitalyisaev2@gmail.com>

# RUN yum -y update
RUN yum -y install python-pip
RUN yum -y install gcc gfortran
RUN yum -y install python-devel
RUN yum -y install gcc-c++
RUN yum -y install python-pandas

RUN pip install networkx 
RUN pip install ipython 

RUN echo "export LANG=en_US.utf8" >> /etc/profile.d/lang.sh

RUN adduser -m vitaly
RUN echo 'vitaly:vitaly' | chpasswd
VOLUME ["/home/vitaly/project"]
WORKDIR /home/vitaly/project
USER vitaly
