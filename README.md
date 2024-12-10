# py-watertank

sudo apt -y update
#sudo apt -y full-upgrade
sudo apt install -y python3-pip python3-dev python3-smbus python3-venv i2c-tools


cd ~/Desktop/ 
ssh-keygen -t rsa -b 4096 -C "blake@blakebowling.com"
cat ~/.ssh/id_rsa.pub
git clone git@github.com:climbingblake/py-watertank.git
cd py-watertank

python3 -m venv venv
source venv/bin/activate

pip install sparkfun-qwiic
pip install streamlit
pip install board
pip install adafruit-blinka
pip install circuitpython-stts22h
pip install plotly
pip install streamlit_autorefresh
pip install streamlit_echarts
pip install lgpio


sudo raspi-config
# Interface >> I2c 

i2cdetect -y 1 # to see if there are devices attached and discovered


# crontab -e
@reboot /usr/bin/env bash -c 'cd /home/pi/Desktop/py-watertank && source venv/bin/activate && streamlit run main.py'


