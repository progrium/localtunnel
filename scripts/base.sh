export PATH=$PATH:/usr/local/sbin/
export PATH=$PATH:/usr/sbin/
export PATH=$PATH:/sbin
apt-get update
apt-get -y install git python2.7-dev python-pip

git clone https://github.com/progrium/localtunnel.git
cd localtunnel
pip install -r requirements.txt
python setup.py install
