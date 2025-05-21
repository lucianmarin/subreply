PREVIOUS=$PWD
cd ~/subreply/
git pull
venv/bin/pip install -U -r requirements.txt
venv/bin/python3 manage.py migrate
pkill -HUP -F sub.pid
cd $PREVIOUS
