
#!/bin/bash
sudo apt install openssh-server

#insted https://docs.docker.com/engine/install/ubuntu/
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

git clone https://github.com/trendy-automation/plc_cv plc_cv

cd plc_cv
cp -ir python docker-compose/appdata
cd docker-compose
docker-compose up --build -d
docker-compose exec agent chown jenkins /var/run/docker.sock