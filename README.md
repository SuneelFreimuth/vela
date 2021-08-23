# Vela (alpha)
A simple framework for Gemini servers inspired by Flask and Express.js.

```python
from vela import Server
# SSL certificate and private key.
app = Server(cert='cert.pem', key='key.pem')

@app.route('/')
def hello(req, res):
    res.send_file('hello.gmi')

PORT = 1965
print(f'Server is listening on port {PORT}...')
app.listen(PORT)
```

## Installation

Through pip:
```shell
pip install vela
```

## Usage

A normal Vela program initializes a `Server` instance, binds one or more handlers to routes, and listens on a port. 1965 is the standard port for Gemini servers.

A `Server` is instantiated with a TLS public certificate and private key. Pass the filenames to the constructor.
```python
from vela import Server
app = Server(cert='cert.pem', key='key.pem')
```

Routes are defined using the `route` decorator, which binds a handler to the route specified by its argument.
```python
@app.route('/')
def root(req, res):
    pass

@app.route('/hello')
def hello(req, res):
    pass

# If you enclose a segment of a route in curly braces, that portion
# will be provided in `req.route.params`.
@app.route('/hello/{name}')
def greet(req, res):
    name = req.route.params['name']
    # ...

# Prepending a * to a route parameter matches all subsequent
# segments, provided as a list.
@app.route('/{greeting}/{*names}')
def greet(req, res):
    names = req.route.params['names']
    for name in names:
        # ...
```
