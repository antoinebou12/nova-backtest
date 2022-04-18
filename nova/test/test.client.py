import socketio

# standard Python
sio = socketio.Client()
sio.connect('http://localhost:5000', wait_timeout=10)
print('my sid is', sio.sid)
sio.emit('MessageStream', {'data': {'message': 'Prise de position sur BTC', 'botId': '0051'}})
