# Subreply

Tiny, but mighty social network. Create an account at https://subreply.com.

## Install

```shell
pip3 install -r requirements.txt
python3 manage.py migrate
```

Create `project/local.py` file and generate `SIGNATURE` for it:

```python
from cryptography.fernet import Fernet
SIGNATURE = Fernet.generate_key()
```

Launch the app at http://localhost:8000 with:

```shell
gunicorn router:app
```

## Styleguide

- easy to read, easy to modify
- no useless abstractions
- speed of 50ms or lower for each request


## License

- ideal to use as internal social network in any organization
- easy to install and easy to maintain 
- cost depends on level of support needed 
