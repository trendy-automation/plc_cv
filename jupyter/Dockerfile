# Pick your favorite docker-stacks image
FROM jupyter/minimal-notebook:2023-02-28

USER root

SHELL ["/bin/bash", "-c"]

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y \
    build-essential \
    cmake \
    git-all \
    software-properties-common \
 && rm -rf /var/lib/apt/lists/*

# Install dependencies: See https://github.com/IntelRealSense/realsense-ros/tree/ros2-development
# Librealsense: See https://github.com/IntelRealSense/librealsense/blob/master/doc/distribution_linux.md#installing-the-packages
RUN apt-get update \
 && apt-key adv --keyserver keyserver.ubuntu.com --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE || apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE \
 && add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo $(lsb_release -cs) main" -u \
 && apt-get install -y \
    librealsense2-dbg \
    librealsense2-dev \
    librealsense2-dkms \
    librealsense2-utils \
 && rm -rf /var/lib/apt/lists/*
 
# Install dep packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \	
    libusb-1.0-0 \
    udev \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

ARG DEBIAN_FRONTEND=dialog

#RUN echo "export PATH=$PATH:~/.local/bin" >> /home/jovyan/.bashrc \
# && echo "export PYTHONPATH=$PYTHONPATH:/opt/conda/lib" >> /home/jovyan/.bashrc \ 
# && echo "export PYTHONPATH=$PYTHONPATH:/opt/conda/lib/python3.10/site-packages/pyrealsense2" >> /home/jovyan/.bashrc

RUN echo "chown -R jovyan /dev/video0" >> /home/jovyan/.bashrc \
 && echo "chown -R jovyan /dev/video1" >> /home/jovyan/.bashrc \
 && echo "chown -R jovyan /dev/video2" >> /home/jovyan/.bashrc \
 && echo "chown -R jovyan /dev/video3" >> /home/jovyan/.bashrc \
 && echo "chown -R jovyan /dev/video4" >> /home/jovyan/.bashrc \
 && echo "chown -R jovyan /dev/video5" >> /home/jovyan/.bashrc \
 && echo "chown -R jovyan /dev/iio:device0" >> /home/jovyan/.bashrc \
 && echo "chown -R jovyan /dev/iio:device1" >> /home/jovyan/.bashrc \
 && echo "chown -R jovyan /dev/HID-SENSOR-2000e1.4.auto" >> /home/jovyan/.bashrc \
 && echo "chown -R jovyan /work" >> /home/jovyan/.bashrc 

 
#USER ${NB_UID}

# Install python packages for data science
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN pip install pyshine