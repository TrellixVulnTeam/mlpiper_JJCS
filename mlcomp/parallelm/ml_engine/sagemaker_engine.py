import datetime
import os

from parallelm.common import constants
from parallelm.common.mlcomp_exception import MLCompException
from parallelm.ml_engine.ee_arg import EeArg
from parallelm.ml_engine.python_engine import PythonEngine


class SageMakerEngine(PythonEngine):
    TYPE = 'sagemaker'

    SERVICE_ROLE_PATH = '/service-role/'
    ROLE_RESPONSE_GROUP = 'Role'
    ROLE_RESPONSE_NAME_KEY = 'RoleName'
    ROLE_RESPONSE_ARN_KEY = 'Arn'

    AWS_DEFAULT_REGION = 'AWS_DEFAULT_REGION'
    AWS_ACCESS_KEY_ID = 'AWS_ACCESS_KEY_ID'
    AWS_SECRET_ACCESS_KEY = 'AWS_SECRET_ACCESS_KEY'

    def __init__(self, pipeline):
        super(SageMakerEngine, self).__init__(pipeline, None)
        self._iam_role = None
        self._iam_role_name = None

        eng_args_config = self._read_execution_env_params()

        self._tag_key = EeArg(eng_args_config.get('tag-key')).value
        self._tag_value = EeArg(eng_args_config.get('tag-value')).value

        self._setup_env(eng_args_config)

        # Note: the 'boto3' module should be imported only after we setup the environment variables,
        # which setup the shared credentials and region configuration
        global boto3, ClientError
        import boto3
        from botocore.exceptions import ClientError

        self._setup_logger(eng_args_config)
        self._setup_iam_role(eng_args_config)

    @property
    def iam_role(self):
        return self._iam_role

    def _setup_iam_role(self, eng_args_config):
        self._iam_role = EeArg(eng_args_config.get('iam_role')).value
        if not self._iam_role:
            # acount_id = boto3.client('sts').get_caller_identity().get('Account')

            now = datetime.datetime.now()
            role_name = 'AmazonSageMaker-ExecutionRole-{y}{month}{d}T{h}{minute}{s}' \
                .format(y=now.year, month=now.month, d=now.day, h=now.hour, minute=now.minute, s=now.second)

            tags = [{'Key': self._tag_key, 'Value': self._tag_value}] if self._tag_key else []

            client = boto3.client('iam')

            try:
                response = client.create_role(
                    Path=SageMakerEngine.SERVICE_ROLE_PATH,
                    RoleName=role_name,
                    AssumeRolePolicyDocument='<URL-encoded-JSON>',
                    Description='Auto generated sagemaker aim role by ParallelM',
                    Tags=tags
                )
                self._iam_role_name = response[SageMakerEngine.ROLE_RESPONSE_GROUP][SageMakerEngine.ROLE_RESPONSE_NAME_KEY]
                self._iam_role = response[SageMakerEngine.ROLE_RESPONSE_GROUP][SageMakerEngine.ROLE_RESPONSE_ARN_KEY]
            except ClientError as e:
                self._logger.error("Failed to create a an iam role for sagemaker service!\n{}".format(e))
                raise e

    def _read_execution_env_params(self):
        ee_config = self._pipeline.get('executionEnvironment', dict()).get('configs')
        if not ee_config:
            raise MLCompException("Missing execution environment section in pipeline json!")

        eng_config = ee_config.get('engConfig')
        if not eng_config:
            raise MLCompException("Missing execution environment engine section in pipeline json!")

        if eng_config['type'] != SageMakerEngine.TYPE:
            raise MLCompException("Unexpected engine type in execution environment! expected: '{}', got: {}"
                                  .format(SageMakerEngine.TYPE, eng_config['type']))

        return eng_config['arguments']

    def _setup_env(self, eng_args_config):
        region = EeArg(eng_args_config.get('region')).value

        aws_access_key_id = EeArg(eng_args_config.get('aws_access_key_id')).value
        if not aws_access_key_id:
            raise MLCompException("Empty 'aws_access_key_id' parameter in execution environment!")

        aws_secret_access_key = EeArg(eng_args_config.get('aws_secret_access_key')).value
        if not aws_secret_access_key:
            raise MLCompException("Missing 'aws_secret_access_key' parameter in execution environment!")

        os.environ[SageMakerEngine.AWS_DEFAULT_REGION] = region
        os.environ[SageMakerEngine.AWS_ACCESS_KEY_ID] = aws_access_key_id
        os.environ[SageMakerEngine.AWS_SECRET_ACCESS_KEY] = aws_secret_access_key

    def _setup_logger(self, eng_args_config):
        logging_level_name = EeArg(eng_args_config.get('logging_level',)).value
        logging_level = constants.LOG_LEVELS.get('info' if not logging_level_name else logging_level_name.lower())
        boto3.set_stream_logger('boto3.resources', logging_level)

    def cleanup(self):
        # TODO: Cleanup all resources that were created during this session.
        # TODO: Add this option to execution environment.
        # TODO: Cleanup according to a given tag, by listing all resources for that tag. The tags
        # TODO: should be assigned when a resource is created.
        if self._iam_role_name:
            client = boto3.client('iam')
            try:
                client.delete_role(RoleName=self._iam_role_name)
            except ClientError as e:
                self._logger.error("Failed to delete the auto-generated iam role for sagemaker service!\n{}"
                                   .format(e))


