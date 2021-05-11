# Cygnus
A simple framework for Gemini servers inspired by Flask.
```python
from cygnus import Server
app = Server()

@app.route('/')
def hello(req, res):
    res.send_file('hello.gmi')

PORT = 5000
print(f'Server is listening on port {PORT}...')
app.listen(PORT)
```
