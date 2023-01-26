pushd %~dp0
powershell Start -File Nettoplcsim-S7o-v-1-2-5-0\bin\NetToPLCsim.exe -Verb RunAs
cd docker-compose
docker-compose up --build -d