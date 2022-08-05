import os
import json
import logging
import datetime
import jsonlines
from yapsy.IPlugin import IPlugin
from modules.common import create_folder
from opentargets_urlzsource import URLZSource
from modules.common.Downloads import Downloads
from modules.common import make_unzip_single_file, make_gzip

logger = logging.getLogger(__name__)


class Expression(IPlugin):
    """
    Expression data collection step implementation
    """

    def __init__(self):
        """
        Constructor, prepare the logging subsystem and a time stamp for the files
        """
        self._logger = logging.getLogger(__name__)
        self.suffix = datetime.datetime.today().strftime('%Y-%m-%d')

    def save_tissue_translation_map(self, output_path, resource, filename):
        """
        Persist tissue translation map information

        :param output_path: destination path
        :param resource: resource information object on the persisting data
        :param filename: source file
        """
        tissues_json = {}
        with URLZSource(filename).open(mode='rb') as r_file:
            tissues_json['tissues'] = json.load(r_file)['tissues']
        # NOTE The following should have been performed by the context handler when exiting the 'with' block
        r_file.close()
        create_folder(os.path.join(output_path, resource.path))
        filename_tissue = os.path.join(output_path, resource.path,
                                       resource.output_filename.replace('{suffix}', self.suffix))
        with jsonlines.open(filename_tissue, mode='w') as writer:
            for item in tissues_json['tissues']:
                entry = {k: v for k, v in tissues_json['tissues'][item].items()}
                entry['tissue_id'] = item
                writer.write(entry)

    def get_tissue_map(self, output, resource):
        """
        Collect and persist tissue map information

        :param output: output folder information
        :param resource: download resource information object
        """
        self.save_tissue_translation_map(output.prod_dir,
                                         resource,
                                         Downloads.download_staging_http(output.staging_dir, resource))

    def get_normal_tissues(self, output, resource):
        """
        Collect normal tissue data, gzip compressed.

        :param output: output folder information object
        :param resource: download resource information object
        """
        filename_unzip = make_unzip_single_file(Downloads.download_staging_http(output.staging_dir, resource))
        gzip_filename = os.path.join(create_folder(os.path.join(output.prod_dir, resource.path)),
                                     resource.output_filename.replace('{suffix}', self.suffix))
        make_gzip(filename_unzip, gzip_filename)

    def process(self, conf, output, cmd_conf=None):
        """
        Expression data collection pipeline step implementation

        :param conf: step configuration object
        :param output: output folder information
        :param cmd_conf: NOT USED
        """
        self._logger.info("Expression step")
        Downloads(output.prod_dir).exec(conf)
        self.get_tissue_map(output, conf.etl.tissue_translation_map)
        self.get_normal_tissues(output, conf.etl.normal_tissues)