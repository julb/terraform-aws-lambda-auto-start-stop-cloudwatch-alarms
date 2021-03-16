import os
import boto3

from base import LambdaFunctionBase


class CWScheduledEventManageAlarmState(LambdaFunctionBase):
    """
    Class changing alarm states of alarm with a specific tag.
    """

    # Section specific to the lambda.
    ACTION = os.environ['PARAM_ACTION']
    RESOURCE_TAG_KEY = os.environ['PARAM_RESOURCE_TAG_KEY']
    RESOURCE_TAG_VALUE = os.environ['PARAM_RESOURCE_TAG_VALUE']
    AWS_REGIONS = os.environ['PARAM_AWS_REGIONS'].split(',')

    def _get_resource_identifiers_by_tag(self, aws_region_name, aws_resource_type, tag_key, tag_value):
        """ Returns all resources identifiers linked to tag. """
        resource_groups_tagging_api_client = boto3.client("resourcegroupstaggingapi", region_name=aws_region_name)
        resource_pages = resource_groups_tagging_api_client.get_paginator('get_resources').paginate(
            TagFilters=[
                {
                    'Key': tag_key,
                    'Values': [
                        tag_value,
                    ]
                },
            ],
            ResourceTypeFilters=[
                aws_resource_type
            ]
        )

        resource_identifiers = []

        for resource_page in resource_pages:
            for resource in resource_page['ResourceTagMappingList']:
                resource_identifier = resource['ResourceARN'].split(':')[-1]
                resource_identifiers.append(resource_identifier)

        return resource_identifiers

    def _disable_alarms(self, aws_region_name, alarm_names):
        """ Disable the alarms. """
        cloudwatch_client = boto3.client('cloudwatch', region_name=aws_region_name)

        self.logger.info('> Disabling alarms.')
        for alarm_name in alarm_names:
            self.logger.info('>> Disabling alarm %s.', alarm_name)
            cloudwatch_client.disable_alarm_actions(AlarmNames=[alarm_name])
            self.logger.info('>> Alarm %s => [DISABLED].', alarm_name)

    def _enable_alarms(self, aws_region_name, alarm_names):
        """ Enable the alarms. """
        cloudwatch_client = boto3.client('cloudwatch', region_name=aws_region_name)

        self.logger.info('> Enabling alarms.')
        for alarm_name in alarm_names:
            self.logger.debug('>> Enabling alarm %s.', alarm_name)
            cloudwatch_client.enable_alarm_actions(AlarmNames=[alarm_name])
            self.logger.info('>> Alarm %s => [ENABLED].', alarm_name)

    def _execute(self, event, context):  # pylint: disable=W0613
        """ Execute the method. """
        self.logger.info('Starting the operation.')

        for aws_region_name in self.AWS_REGIONS:
            self.logger.info('> Searching CloudWatch alarms in region %s having tag %s=%s.',
                             aws_region_name, self.RESOURCE_TAG_KEY, self.RESOURCE_TAG_VALUE)

            # Get Alarms by tag.
            alarm_names = self._get_resource_identifiers_by_tag(aws_region_name, "cloudwatch:alarm", self.RESOURCE_TAG_KEY, self.RESOURCE_TAG_VALUE)

            self.logger.info('> Found %s alarms in region %s having tag %s=%s.',
                             str(len(alarm_names)), aws_region_name, self.RESOURCE_TAG_KEY, self.RESOURCE_TAG_VALUE)

            # Enable/Disable
            if len(alarm_names) > 0:
                if self.ACTION in ['enable', 'start']:
                    self._enable_alarms(aws_region_name, alarm_names)
                elif self.ACTION in ['disable', 'stop']:
                    self._disable_alarms(aws_region_name, alarm_names)

        self.logger.info('Operation completed successfully.')

        return self._build_response_ok()


def lambda_handler(event, context):
    """ Function invoked by AWS. """
    return CWScheduledEventManageAlarmState().process_event(event, context)
