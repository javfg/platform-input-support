import os
import logging
import google.auth
from datetime import datetime
from google.cloud import storage, exceptions
from modules.common import extract_date_from_file

logger = logging.getLogger(__name__)


class GoogleBucketResource(object):

    # args -- tuple of anonymous arguments | kwargs -- dictionary of named arguments
    # def __init__(self, *args, **kwargs):
    def __init__(self, bucket_name=None, path=None):
        self.bucket_name = bucket_name  # kwargs.get('bucket_name')[0] if kwargs.get('bucket_name')[0] != "" else None
        self.object_path = path  # kwargs.get('bucket_name')[1] if len(kwargs.get('bucket_name')) == 2 else None
        # Issue detect Upload of large files times out. #40
        # storage.blob._DEFAULT_CHUNKSIZE = 5 * 1024 * 1024  # 5 MB
        # storage.blob._MAX_MULTIPART_SIZE = 5 * 1024 * 1024  # 5 MB
        self.client = storage.Client()

    def __del__(self):
        logger.debug('Destroyed instance of %s', __name__)

    @staticmethod
    def has_valid_auth_key(google_credential_key=None):
        """
        Check whether the available Google Cloud Access key is valid or not

        :param google_credential_key: Google Cloud access credentials file
        :return: True if valid, False otherwise
        """
        if google_credential_key is None:
            logger.info("gsutil will use the default credential for the user.")
        else:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_credential_key
        try:
            credentials, project = google.auth.default()
        except Exception as error:
            logger.error('Google Auth Error: %s', error)
        else:
            logger.info('\n\tGoogle Bucket connection: %s', project)
            return True
        return False

    @staticmethod
    def get_bucket_and_path(google_bucket_param):
        """
        Separate the Google Storage Bucket name from the path within that bucket

        :param google_bucket_param: Google Cloud Bucket full path, without scheme, e.g. gcp_bucket_name/path/to/...
        """
        if google_bucket_param is None:
            return None, None
        split = google_bucket_param.split('/', 1) + [None]
        return split[0], split[1]

    def get_full_path(self):
        """
        Get the full Google Storage Bucket Path, including the bucket name

        :return: full Google Storage Bucket Path
        """
        if self.object_path is not None:
            return self.bucket_name + '/' + self.object_path
        return self.bucket_name

    # NOTE This method is not being used anywhere
    def get_list_buckets(self):
        """
        Retrieve the list of Google Storage Buckets available to the user

        :return: list of available buckets
        """
        return self.client.list_buckets()

    # Retrieve the list of buckets available for the user
    def get_bucket(self):
        """
        Get a reference to the Google Cloud Bucket in this resource instance

        :return: a reference to the specified bucket in this instance, None otherwise
        """
        if self.bucket_name is None:
            logger.error("No bucket name has been provided for this resource instance")
        else:
            try:
                bucket = self.client.get_bucket(self.bucket_name)
                return bucket
            except google.cloud.exceptions.NotFound:
                logger.error("Sorry, that bucket {} does not exist!".format(self.bucket_name))
            except exceptions.Forbidden:
                logger.error(" ERROR: GCS forbidden access, path={}".format(self.bucket_name))
        return None

    # For instance you can call the method
    # google_resource.list_blobs('bucket_name/directory/','/', None, None)
    def list_blobs(self, prefix, delimiter='', include=None, exclude=None):
        """
        List BLOBs in a Google Storage Bucket

        :param prefix: Google Storage Bucket Path, including bucket name
        :param delimiter: Path separator, default ''
        :param include: optionally specify information on which BLOBs should be the only ones included in the listing,
        default None
        :param exclude: optionally specify information on which BLOBs should be excluded from the listing, this takes
        precedence over the 'included' information, default None
        :return: a map from BLOB name to its 'created' and 'updated' time stamps
        """
        list_blobs_dict = {}
        bucket = self.client.get_bucket(self.bucket_name)
        if bucket is not None:
            blobs = bucket.list_blobs(prefix=prefix, delimiter=delimiter)

            for blob in blobs:
                logger.debug("Filename: %s , Created: %s, Updated: %s", blob.name, blob.time_created, blob.updated)
                if ((exclude is not None) and (exclude in blob.name)
                        or (include is not None) and (include not in blob.name)):
                    continue
                list_blobs_dict[blob.name] = {'created': blob.time_created, 'updated': blob.updated}
        return list_blobs_dict

    def list_blobs_object_path(self):
        """
        List BLOBs for the given object path configured in this resource instance

        :return: a map from BLOB name to its 'created' and 'updated' time stamps
        """
        return self.list_blobs(self.object_path)

    def list_blobs_object_path_excludes(self, excludes_pattern):
        """
        List BLOBs for the given object path configured in this resource instance, but given an exclusion pattern

        :param excludes_pattern: exclusion pattern to be used when building the BLOB listing
        :return: a map from BLOB name to its 'created' and 'updated' time stamps
        """
        return self.list_blobs(self.object_path, exclude=excludes_pattern)

    def list_blobs_object_path_includes(self, included_pattern):
        """
        List BLOBs for the given object path configured in this resource instance, but given an inclusion pattern

        :param included_pattern: inclusion pattern to be used when building the BLOB listing
        :return: a map from BLOB name to its 'created' and 'updated' time stamps
        """
        return self.list_blobs(self.object_path, include=included_pattern)

    # WARNING - UNUSED - REMOVE - DEPRECATE
    def copy_from(self, original_filename, dest_filename, gs_specific_output_dir=None):
        bucket_link = self.get_bucket()
        if bucket_link is None:
            raise ValueError('Invalid google storage bucket {bucket}'.format(bucket=self.bucket_name))

        object_path = self.object_path
        if gs_specific_output_dir is not None:
            object_path = object_path + '/' + gs_specific_output_dir

        blob = bucket_link.blob(object_path + '/' + dest_filename)
        logger.info('Copy the file %s to the bucket %s', original_filename, bucket_link)
        if ".gz" in original_filename:
            blob.content_type = "application/x-gzip"
        else:
            blob.content_type = "text/plain"

        blob.upload_from_filename(filename=original_filename)
        return blob.name

    # NOTE General helper method that should be refactored out of this class into a Spark related Helper module
    @staticmethod
    def is_a_spark_directory(filename):
        """
        Check whether a given path is a Spark directory or not

        :return: True if the given path is a Spark directory, False otherwise
        """
        if (filename.find("/_SUCCESS") > 0) \
                or (filename.find("/part-0") > 0) \
                or (filename.find("/.part-0") > 0) \
                or (filename.find("/._") > 0):
            return True
        return False

    def extract_latest_file(self, list_blobs):
        """
        Return the filename with the latest date within the given BLOB listing, managing collisions only for the latest
        date

        :param list_blobs: BLOB listing to use as source for the file with the latest date
        :raise ValueError: if multiple entries are found to have the same date
        :return: the file name with the latest date
        """
        last_recent_file = None
        possible_recent_date_collision = False
        recent_date = datetime.strptime('01-01-1900', '%d-%m-%Y')
        for filename in list_blobs:
            date_file = extract_date_from_file(filename)
            if date_file:
                if date_file == recent_date:
                    if not self.is_a_spark_directory(filename):
                        possible_recent_date_collision = True
                    else:
                        # it is spark dir. Check if it is the same dir
                        if os.path.dirname(filename) != os.path.dirname(last_recent_file):
                            logger.info("'{}' vs '{}'".format(filename, last_recent_file))
                            possible_recent_date_collision = True
                if date_file > recent_date:
                    possible_recent_date_collision = False
                    recent_date = date_file
                    last_recent_file = filename
        if possible_recent_date_collision:
            # Raise an error. No filename is unique in the recent date selected.
            msg = "Error TWO files with the same date: '{}' and '{}'".format(last_recent_file,
                                                                             recent_date.strftime('%d-%m-%Y'))
            logger.error(msg)
            raise ValueError(msg)
        logger.info("Latest file: %s %s", last_recent_file, recent_date.strftime('%d-%m-%Y'))
        return {"latest_filename": last_recent_file,
                "suffix": recent_date.strftime('%Y-%m-%d'), "spark": self.is_a_spark_directory(last_recent_file)}

    def get_latest_file(self, resource_info):
        """
        Get the latest 'entity' given a resource information

        :param resource_info: Resource information where to extract latest entity from
        :return: latest entity in resource
        """
        if 'excludes' in resource_info:
            list_blobs = self.list_blobs_object_path_excludes(resource_info.excludes)
        elif 'includes' in resource_info:
            list_blobs = self.list_blobs_object_path_includes(resource_info.includes)
        else:
            list_blobs = self.list_blobs_object_path()
        latest_filename_info = self.extract_latest_file(list_blobs)
        return latest_filename_info

    def download_dir(self, dir_to_download, local_dir):
        """
        Download the files from a given folder in the current bucket into the given local folder

        :param dir_to_download: bucket path where to download the files from
        :param local_dir: local destination for the downloaded files
        :return: a list of local paths to the downloaded files
        """
        list_files = []
        dir_name = os.path.dirname(dir_to_download)  # dir_to_download.rsplit("/", 1)[0]
        # WARNING bucket could be 'None'
        for blob in self.get_bucket().list_blobs(prefix=dir_name):
            folder, filename = os.path.split(blob.name)
            filename_destination = os.path.join(local_dir, filename)
            blob.download_to_filename(filename_destination)
            list_files.append(filename_destination)
        return list_files

    def download_file(self, src_path_file, dst_path_file):
        """
        Download a specific file from the current bucket

        :param src_path_file: source file path to download
        :param dst_path_file: destination file path for the downloaded file
        :return: destination file path of the downloaded file
        """
        self.get_bucket()\
            .blob(src_path_file)\
            .download_to_filename(dst_path_file)
        return dst_path_file

    def download(self, download_descriptor):
        """
        Download 'something', it could be an entire folder or just a file, described by the given download descriptor

        :return: a file path listing for the downloaded files in case the download descriptor describes a folder, or a
        destination file path in case it describes a file
        """
        if download_descriptor["is_dir"]:
            return self.download_dir(download_descriptor["file"], download_descriptor["output"])
        return self.download_file(download_descriptor["file"], download_descriptor["output"])

    def blob_metadata(self, blob_name):
        """
        Prints out a blob's metadata for the given BLOB name

        :param blob_name: BLOB name to print metadata for
        """
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(self.bucket_name)
        blob = bucket.get_blob(blob_name)

        print(('Blob: {}'.format(blob.name)))
        print(('Bucket: {}'.format(blob.bucket.name)))
        print(('Storage class: {}'.format(blob.storage_class)))
        print(('ID: {}'.format(blob.id)))
        print(('Size: {} bytes'.format(blob.size)))
        print(('Updated: {}'.format(blob.updated)))
        print(('Generation: {}'.format(blob.generation)))
        print(('Metageneration: {}'.format(blob.metageneration)))
        print(('Etag: {}'.format(blob.etag)))
        print(('Owner: {}'.format(blob.owner)))
        print(('Component count: {}'.format(blob.component_count)))
        print(('Crc32c: {}'.format(blob.crc32c)))
        print(('md5_hash: {}'.format(blob.md5_hash)))
        print(('Cache-control: {}'.format(blob.cache_control)))
        print(('Content-type: {}'.format(blob.content_type)))
        print(('Content-disposition: {}'.format(blob.content_disposition)))
        print(('Content-encoding: {}'.format(blob.content_encoding)))
        print(('Content-language: {}'.format(blob.content_language)))
        print(('Metadata: {}'.format(blob.metadata)))

        if blob.retention_expiration_time:
            print(("retentionExpirationTime: {}"
                   .format(blob.retention_expiration_time)))