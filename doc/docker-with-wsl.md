WSL with docker setup

wsl --install <distro>
wsl --set-default-version <1/2>
wsl --set-default <distro>
sudo apt update && sudo apt upgrade

wsl.exe --list --online
wsl.exe --list --verbose OR wsl -l -v
wsl.exe --distribution <DistroName>


lsb_release -a : check ubuntu version
wsl --terminate <distro> : stop the distro
wsl --unregister <distro> : unregister (delete) the distro


(INSTALL DOCKER ENGINE)
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo docker run hello-world

sudo groupadd docker
sudo usermod -aG docker $USER

