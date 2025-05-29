# Subreply

Tiny, but mighty social network. Create an account at [subreply.com](https://subreply.com/).

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

## Coding

- speed of 50ms or lower for each page request
- clean code: easy to read, easy to modify
