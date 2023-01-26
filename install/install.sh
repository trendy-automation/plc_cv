#!/bin/bash
sudo apt install -y openssh-server

#insted https://docs.docker.com/engine/install/ubuntu/
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER
sudo apt  install -y docker-compose 

git clone https://github.com/trendy-automation/plc_cv plc_cv

cd plc_cv
cp -ir python docker-compose/appdata/python
cd docker-compose
#sudo docker volume create portainer_data

sudo chmod +x appdata/python/appstart.sh

sudo docker-compose up --build -d
sudo docker-compose exec agent chown jenkins /var/run/docker.sock
sudo docker-compose exec jenkins cat var/jenkins_home/secrets/initialAdminPassword