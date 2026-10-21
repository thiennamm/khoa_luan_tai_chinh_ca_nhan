from django.core.files.uploadhandler import FileUploadHandler, StopUpload


class CsvSizeLimitHandler(FileUploadHandler):
    """Giới hạn trước khi upload được chuyển vào bộ nhớ/tệp tạm Django."""
    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        self.received = 0

    def receive_data_chunk(self, raw_data, start):
        self.received += len(raw_data)
        if self.received > 2 * 1024 * 1024:
            self.request.csv_upload_too_large = True
            raise StopUpload(connection_reset=False)
        return raw_data

    def file_complete(self, file_size):
        return None
