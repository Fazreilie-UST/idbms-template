# Setup
install nodeJS, verify with "node -v"

(NodeJS Windows installation)
npm create vite@latest frontend -- --template react
npm install react-router-dom axios (routing)

(NodeJS WSL Installation)

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc OR source ~/.zshrc
nvm install --lts
nvm use --lts
node -v
npm -v


(Frontend Setup)
- install Node and NPM
- npm ci
- npm run dev



# has error during build?
npm cache clean --force
(might need to run this in Powershell first) Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
