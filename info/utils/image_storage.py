
from qiniu import  Auth, put_data

access_key = 'rw5On7WGZ2b3gcR6FGmq9_O2QpPIEDIQewiY5lWF'
secret_key = 'FHESfx6yr-ZqUieJtpHQZbCPnL3HRtf4mcIm-cSD'
bucket_name = 'information'

def storage(data): # 参数传入二进制图片、文件
    try:
        q = Auth(access_key, secret_key)
        token = q.upload_token(bucket_name)
        ret, info = put_data(token, None, data)
    except Exception as e:
        raise e
    if  info.status_code != 200:
        raise Exception('图片上传失败')
    return ret['key']

if __name__ == '__main__':
    file = input('输入文件路径')
    with open(file, 'rb') as f:
        storage(f.read())