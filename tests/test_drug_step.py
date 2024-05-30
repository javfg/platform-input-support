import unittest
from pathlib import Path
from unittest.mock import patch

from addict import Dict

from platform_input_support import ROOT_DIR
from platform_input_support.modules.common.yaml_reader import YAMLReader
from platform_input_support.plugins import drug


class TestDrugStep(unittest.TestCase):
    """YamlReader reads the 'config.yaml' file in the base directory and returning a dictionary representation."""

    def setUp(self):
        default_conf_file = Path(ROOT_DIR) / 'config.yaml'
        self.yaml_reader = YAMLReader(default_conf_file)
        self.config = self.yaml_reader.read_yaml()
        self.output = self.create_output_dir_test()

    def create_output_dir_test(self):
        output = Dict()
        output.prod_dir = 'output/prod'
        output.staging_dir = 'ouput/staging'
        return output

    @patch('platform_input_support.plugins.Drug.Drug._download_elasticsearch_data')
    def test_output_has_fields_to_write_to_gcp(self, mock1):
        """
        Should return a dictionary with GCP target directory.

        So that if `RetrieveResource` is configured to upload results it can save the files somewhere valid.
        """
        # Given
        # file names 'saved' by step
        es_return_values = ['f1', 'f2', 'f3']
        mock1.return_value = es_return_values
        # We only want to test the results of ES configuration at this point.
        es_config = self.config.steps.drug
        es_config.datasources.pop('downloads', None)
        # When
        drug_step = drug.Drug()
        results = drug_step.download_indices(self.config.steps.drug, self.output)
        # Then
        # Each file saved should be in returned dictionary
        assert len(results) == len(es_return_values)
        # returned dictionary should have fields 'resource' and 'gs_output_dir'
        for f in es_return_values:
            assert f in results
