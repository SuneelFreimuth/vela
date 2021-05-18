# Vela (alpha)
A simple framework for Gemini servers inspired by Flask and Express.js.

```python
from vela import Server
# SSL certificate and private key.
app = Server(cert='cert.pem', key='key.pem')

@app.route('/')
def hello(req, res):
    res.send_file('hello.gmi')

PORT = 5000
print(f'Server is listening on port {PORT}...')
app.listen(PORT)
```
