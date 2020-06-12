PREVIOUS=$PWD
cd ~/subreply/
git pull
python3 manage.py migrate
pkill -HUP -F sub.pid
cd $PREVIOUS
