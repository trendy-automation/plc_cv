# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# Pick your favorite docker-stacks image
FROM jupyter/minimal-notebook:2023-02-28

USER root

# Add permanent apt-get installs and other root commands here
# e.g., RUN apt-get install --yes --no-install-recommends npm nodejs
RUN apt update
#RUN apt install libudev0:i386
RUN apt -y install libusb-1.0-0-dev && apt-get install ffmpeg libsm6 libxext6  -y

USER ${NB_UID}

# Switch back to jovyan to avoid accidental container runs as root
# Add permanent mamba/pip/conda installs, data files, other user libs here
# e.g., RUN pip install --no-cache-dir flake8




# Install python packages for data science
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

