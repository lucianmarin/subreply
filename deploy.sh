PREVIOUS=$PWD
cd ~/falcondub/
git pull
python3 manage.py migrate
pkill -HUP -F dub.pid
cd $PREVIOUS
