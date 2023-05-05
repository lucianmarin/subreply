PREVIOUS=$PWD
cd ~/subreply/
git pull
python3 -m pip install -U -r requirements.txt --break-system-packages
python3 manage.py migrate
pkill -HUP -F sub.pid
cd $PREVIOUS
