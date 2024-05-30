from loguru import logger
from yapsy.IPlugin import IPlugin

from platform_input_support.manifest import ManifestStatus, get_manifest_service
from platform_input_support.modules.common.downloads import Downloads


class Evidence(IPlugin):
    """Evidence data collection step."""

    def __init__(self):
        """Evidence class constructor."""
        self.step_name = 'Evidence'

    def process(self, conf, output, cmd_conf=None):
        """Evidence pipeline step implementation.

        :param conf: step configuration object
        :param output: output folder information
        :param cmd_conf: UNUSED
        """
        logger.info('[STEP] BEGIN, Evidence')
        manifest_service = get_manifest_service()
        manifest_step = manifest_service.get_step(self.step_name)
        manifest_step.resources.extend(Downloads(output.prod_dir).exec(conf))
        get_manifest_service().compute_checksums(manifest_step.resources)
        if not get_manifest_service().are_all_resources_complete(manifest_step.resources):
            manifest_step.status_completion = ManifestStatus.FAILED
            manifest_step.msg_completion = 'COULD NOT retrieve all the resources'
        # TODO - Validation
        if manifest_step.status_completion != ManifestStatus.FAILED:
            manifest_step.status_completion = ManifestStatus.COMPLETED
            manifest_step.msg_completion = 'The step has completed its execution'
        logger.info('[STEP] END, Evidence')
