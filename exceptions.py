class GrUrlError(Exception):
    def __init__(self, message=''):
        if message != '':
            self.message = message


class GrResponseError(Exception):
    def __init__(self, err_code, err_msg):
        self.message = f'Error code: {err_code}, Error message: {err_msg}'
