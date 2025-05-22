# Subreply

Tiny, but mighty social network. Create an account at [subreply.com](https://subreply.com/).

## Install

```shell
pip install -r requirements.txt
```

Generate `SIGNATURE` for `project/local.py`:

```python
from cryptography.fernet import Fernet
SIGNATURE = Fernet.generate_key()
```

## Speed

The target is 50ms or lower for each page request.

## Code

- clean code only
- easy to read, easy to modify
