from django.core.files.storage import Storage
from django.conf import settings

from fdfs_client.client import Fdfs_client, get_tracker_conf

class FDFSStorage(Storage):
    '''fastdfs文件存储类'''

    def __init__(self, client_conf=None, base_url=None):
        if client_conf == None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if base_url == None:
            base_url = settings.FDFS_STORAGE_URL
        self.base_url = base_url


    def _open(self, name, mode='rb'):
        pass

    def _save(self, name, context):
        # C:\Users\lzj\Desktop\df\utils\fdfs\client.conf
        trackers = get_tracker_conf(self.client_conf)
        client = Fdfs_client(trackers)
        res = client.upload_appender_by_buffer(context.read())
        # dict
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',
        #     'Local file name': local_file_name,
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # }
        if res.get('Status') != 'Upload successed.':
            raise Exception('上传失败')

        filename = res.get('Remote file_id')
        # return filename.encode()
        return filename

    def exists(self, name):
        return False

    def url(self, name):
        return self.base_url + name