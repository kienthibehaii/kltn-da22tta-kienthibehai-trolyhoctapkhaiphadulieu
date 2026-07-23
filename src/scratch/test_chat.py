# -*- coding: utf-8 -*-
import urllib.request
import json

def test():
    url = 'http://127.0.0.1:3000/api/chat'
    data = {
        'thread_id': 'thread-test-999',
        'messages': [
            {'role': 'user', 'content': 'Đề cương môn Khai phá DL gồm các chương nào?'}
        ]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        response = urllib.request.urlopen(req)
        res_data = json.loads(response.read().decode('utf-8'))
        print("SUCCESS RESPONSE:")
        print(res_data.get('text'))
    except Exception as e:
        print("ERROR:", str(e))

if __name__ == '__main__':
    test()
