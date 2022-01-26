import json
import logging
import requests

from requests import ConnectionError
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, utils

logger = logging.getLogger(__name__)


class ElasticsearchInstance(object):
    """
    Wrapper over an Elasticsearch instance.
    """

    def __init__(self, host, port, scheme='http'):
        """
        Constructor

        :param host: Elastic Search Host information
        :param port: Elastic Search Port information
        :param scheme: which access scheme to use for accessing the given Elastic Search Instance
        """
        self._port = port
        self._host = host
        self._scheme = scheme
        logger.info("Creating Elastic Search Instance Wrapper with host: {}, port: {}".format(self._host, self._port))
        self.es = Elasticsearch([{'host': self._host, 'port': self._port}])

    def is_reachable(self):
        """
        Pings configured Elasticsearch instance and returns true if reachable, false otherwise
        """
        try:
            request = requests.head("http://{}:{}".format(self._host, self._port), timeout=1)
            return request.ok
        except ConnectionError as error:
            logger.error("Unable to reach {}. Error msg: ".format(self._host, error))
        return False

    def get_fields_on_index(self, index, outfile, fields=None, pagesize=1000):
        """
        Return all documents from `index` returning only the `fields` specified.
        :param index: Elasticsearch index to query as Str
        :param outfile: file to save results of query
        :param fields: subset of fields to return as List[Str]
        :param pagesize: number of documents to buffer before writing
        :return: List of dictionary entries including `fields` if available.
        """

        def _process_hit_value(field_value):
            """
            :param field_value: Value wrapped in an Elasticsearch wrapper
            :return: Json serializable version of v
            """
            if isinstance(field_value, utils.AttrList):
                return field_value._l_
            elif isinstance(field_value, utils.AttrDict):
                return field_value._d_
            else:
                return field_value

        size = pagesize
        doc_count = 0
        doc_buffer = []
        # set up es query
        s = Search(index=index, using=self.es)
        s = s.source(fields=list(fields))
        # execute query: scan acts as a cursor until all index docs are read.
        for hit in s.scan():
            hit_dict = {}
            for f in fields:
                if f in hit:
                    hit_dict[f] = _process_hit_value(hit[f])
                else:
                    logger.error("field \"%s\" not found on document from index: %s", f, index)
            doc_buffer.append(hit_dict)
            # write buffer to file, update document count, and clear buffer
            if len(doc_buffer) >= size:
                self.write_elasticsearch_docs_as_jsonl(doc_buffer, outfile)
                doc_count += len(doc_buffer)
                doc_buffer = []
        # save final docs from partial page.
        if doc_buffer:
            self.write_elasticsearch_docs_as_jsonl(doc_buffer, outfile)
            doc_count += len(doc_buffer)
        return doc_count

    def write_elasticsearch_docs_as_jsonl(self, docs, fname):
        """
        Write list of elasticsearch objects to file as jsonl format.
        :param fname: file to write contents of `doc`. New docs are appended to file if it exists.
        :param docs: List of elasticsearch documents represented as dictionaries. Each document will be written as a
        standalone json object (jsonl).
        :return: None
        """
        with open(fname, 'a+') as outfile:
            for doc in docs:
                json.dump(doc, outfile)
                outfile.write('\n')
        logger.debug("Wrote {} documents to {}.".format(len(docs), fname))
