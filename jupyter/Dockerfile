# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# Pick your favorite docker-stacks image
FROM jupyter/minimal-notebook:2023-02-28

USER root

# Add permanent apt-get installs and other root commands here
# e.g., RUN apt-get install --yes --no-install-recommends npm nodejs
# RUN apt update && apt -y install libusb-1.0-0-dev && apt -y install ffmpeg libsm6 libxext6

RUN apt-get update \
 && apt-key adv --keyserver keyserver.ubuntu.com --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE || apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE \
 && add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo $(lsb_release -cs) main" -u \
 && apt-get install -y \
    librealsense2-dbg \
    librealsense2-dev \
    librealsense2-dkms \
    librealsense2-utils \
 && rm -rf /var/lib/apt/lists/*

USER ${NB_UID}

# Switch back to jovyan to avoid accidental container runs as root
# Add permanent mamba/pip/conda installs, data files, other user libs here
# e.g., RUN pip install --no-cache-dir flake8




# Install python packages for data science
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

