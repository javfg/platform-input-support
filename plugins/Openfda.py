import os
import json
import tqdm
import logging
import multiprocessing as mp
from yapsy.IPlugin import IPlugin
from modules.common import create_folder
from modules.common.Downloads import Downloads
from plugins.helpers.OpenfdaHelper import OpenfdaHelper

logger = logging.getLogger(__name__)

"""
This module gathers all data related to OpenFDA FAERS database, with a focus on Drug Events.

In addition, a collection of blacklisted events is downloaded for later use in the ETL backend pipeline.
"""


class Openfda(IPlugin):
    """
    This class implements the OpenFDA data collection step
    """
    def __init__(self):
        """
        Constructor, prepares logging subsystem
        """
        self._logger = logging.getLogger(__name__)

    def _download_selected_event_files(self, repo_metadata, output):
        """
        Collect a subset of the available OpenFDA data, described by the given repository metadata, into a specified
        destination folder

        :param repo_metadata: OpenFDA repository metadata
        :param output: output folder for the collected OpenFDA data
        :return it should return information on the downloaded files, but, in fact, that information is empty
        """
        # TODO Collect the information on the produced / downloaded files into the output directory by using a thread
        #  safe version of Dict() or maybe Futures... etc.
        downloaded_files = dict()
        # Body
        if repo_metadata:
            self._logger.info("OpenFDA FAERs metadata received")
            fda_output = create_folder(os.path.join(output.prod_dir, "fda-inputs"))
            fda = OpenfdaHelper(fda_output)
            # Parallel data gathering
            self._logger.info("Prepare download pool of {} processes".format(mp.cpu_count()))
            download_pool_nprocesses = mp.cpu_count() * 2
            download_pool_chunksize = int(
                len(repo_metadata['results']['drug']['event']['partitions']) / download_pool_nprocesses
            )
            with mp.Pool() as download_pool:
                self._logger.info(mp.current_process())
                try:
                    for _ in tqdm.tqdm(download_pool.map(fda._do_download_openfda_event_file,
                                                         repo_metadata['results']['drug']['event']['partitions'],
                                                         chunksize=download_pool_chunksize),
                                       total=len(repo_metadata['results']['drug']['event']['partitions'])):
                        self._logger.info('\rdone {0:%}'.format(_ / len(repo_metadata['results']['drug']['event']['partitions'])))
                except Exception as e:
                    self._logger.info("Something went wrong: " + str(e))
        return downloaded_files

    def _download_openfda_faers(self, resource, output):
        """
        Get OpenFDA repository metadata and kick start the OpenFDA data collection process

        :param resource: download descriptor for OpenFDA repository metadata file
        :param output: output folder for the data collection
        :return: information on the downloaded files
        """
        self._logger.info("OpenFDA available files download, URI '{}' --- START ---".format(resource.uri))
        downloaded_files = dict()
        self._logger.info("Download OpenFDA FAERS repository metadata")
        download = Downloads.download_staging_http(output.staging_dir, resource)
        repo_metadata = {}
        with open(download, 'r') as f:
            repo_metadata = json.load(f)
        downloaded_event_files = self._download_selected_event_files(repo_metadata, output)
        downloaded_files.update(downloaded_event_files)
        return downloaded_files

    def process(self, conf, output, cmd_conf=None):
        """
        OpenFDA data collection step implementation

        :param conf: OpenFDA step configuration object
        :param output: output folder for collected OpenFDA data
        :param cmd_conf: UNUSED
        """
        self._logger.info("Openfda step")
        Downloads(output.prod_dir).exec(conf)
        self._download_openfda_faers(conf.etl.downloads, output)