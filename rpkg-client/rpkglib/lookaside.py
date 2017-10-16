import requests
import pyrpkg.lookaside


class CGILookasideCache(pyrpkg.lookaside.CGILookasideCache):
    """A class to interact with a CGI-based lookaside cache"""
    def __init__(self, hashtype, download_url, upload_url,
                 client_cert=None, ca_cert=None):
        super(CGILookasideCache, self).__init__(hashtype, download_url, upload_url,
                                                client_cert=client_cert,ca_cert=ca_cert)

        self.old_download_path = '%(name)s/%(filename)s/%(hash)s/%(filename)s'
        self.new_download_path = '%(name)s/%(filename)s/%(hashtype)s/%(hash)s/%(filename)s'

    def download(self, name, filename, hash, outfile, hashtype=None, **kwargs):
        original_download_path = self.download_path
        urled_file = filename.replace(' ', '%20')
        path_dict = {'name': name, 'filename': urled_file, 'hash': hash,
                     'hashtype': hashtype}
        path_dict.update(kwargs)

        for download_path in [self.old_download_path, self.new_download_path]:
            path = download_path % path_dict
            url = '%s/%s' % (self.download_url, path)
            response = requests.head(url)
            self.log.debug("URL %s returned status %s" % (url, response.status_code))
            if response.status_code == 200:
                self.log.debug("This URL seems to be correct, using it")
                self.download_path = download_path
                break

        result = super(CGILookasideCache, self).download(name, filename, hash, outfile, hashtype=hashtype, **kwargs)
        self.download_path = original_download_path
        return result
