import pytest
import uuid
import os
import logging
import json

from parallelm.ml_engine.sagemaker_engine import SageMakerEngine
from parallelm.pipeline.components_desc import ComponentsDesc
from parallelm.ml_engine.python_engine import PythonEngine
from parallelm.pipeline.dag import Dag
from parallelm.pipeline.executor import Executor, ExecutorException
from parallelm.pipeline.executor_config import ExecutorConfig

import parallelm.pipeline.json_fields as json_fields

from constants import REFLEXCOMMON_PATH

class TestPythonEngine:

    system_config = {
                 "statsDBHost": "localhost",
                 "statsDBPort": 8086,
                 "mlObjectSocketSinkPort": 7777,
                 "mlObjectSocketSourcePort": 1,
                 "workflowInstanceId": "8117aced55d7427e8cb3d9b82e4e26ac",
                 "statsMeasurementID": "1",
                 "modelFileSourcePath": "__fill_in_real_model__"
     }

    @staticmethod
    def _get_mlcomp_jar():
        dirname = os.path.dirname(__file__)

        # Need to move this code to a helper module which will info about the structure of the code
        reflex_common = os.path.join(dirname, REFLEXCOMMON_PATH)
        mlcomp_jar = os.path.join(reflex_common, "mlcomp", "target", "mlcomp.jar")
        if not os.path.exists(mlcomp_jar):
            raise Exception("File: {} does not exists".format(mlcomp_jar))
        return mlcomp_jar

    @staticmethod
    def _gen_model_file():
        model_file = os.path.join("/tmp", "model_file_" + str(uuid.uuid4()))
        with open(model_file, "w") as ff:
            ff.write("model-1234")
        return model_file

    @staticmethod
    def _fix_pipeline(pipeline, model_file, **kwargs):
        system_config = TestPythonEngine.system_config
        system_config["modelFileSourcePath"] = model_file
        for key, value in kwargs.items():
            system_config[key] = value
        pipeline["systemConfig"] = system_config

    def _get_executor_config(self, pipeline):
        config = ExecutorConfig(pipeline=json.dumps(pipeline),
                                pipeline_file=None,
                                run_locally=False,
                                mlcomp_jar=self._get_mlcomp_jar())
        return config

    # Note, skip lines are commented so can be easily uncommented when debugging
    def test_dag_detect_is_stand_alone(self):

        pipeline = {
            "name": "stand_alone_test",
            "engineType": "Generic",

            "pipe": [
                {
                    "name": "Hello",
                    "id": 1,
                    "type": "hello-world",
                    "parents": [],
                    "arguments": {
                        "arg1": "arg1-value"
                    }
                }
            ]
        }
        python_engine = PythonEngine("test-pipe")
        comps_desc_list = ComponentsDesc(python_engine, pipeline=pipeline).load()
        dag = Dag(pipeline, comps_desc_list, python_engine)
        assert dag.is_stand_alone is True

    # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_execute_python_stand_alone(self):
        pipeline = {
            "name": "stand_alone_test",
            "engineType": "Generic",

            "pipe": [
                {
                    "name": "Hello",
                    "id": 1,
                    "type": "hello-world",
                    "parents": [],
                    "arguments": {
                        "arg1": "arg1-value"
                    }
                }
            ]
        }
        self._fix_pipeline(pipeline, None)
        config = self._get_executor_config(pipeline)
        Executor(config).go()

    # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_execute_python_stand_alone_with_argument_from_env_var(self):
        pipeline = {
            "name": "stand_alone_test",
            "engineType": "Generic",

            "pipe": [
                {
                    "name": "Hello",
                    "id": 1,
                    "type": "test-argument-from-env-var",
                    "parents": [],
                    "arguments": {
                        "arg1": "test-value",
                        "fromEnvVar2": "test-value2",
                    },
                }
            ]
        }
        self._fix_pipeline(pipeline, None)
        config = self._get_executor_config(pipeline)
        os.environ.setdefault("TEST_VAR", "test-value")
        os.environ.setdefault("TEST_VAR2", "non test value")
        Executor(config).go()

    # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_execute_python_stand_alone_with_exit_0(self):
        pipeline = {
            "name": "stand_alone_test",
            "engineType": "Generic",

            "pipe": [
                {
                    "name": "Hello",
                    "id": 1,
                    "type": "test-argument-from-env-var",
                    "parents": [],
                    "arguments": {
                        "arg1": "test-exit-0",
                        "fromEnvVar2": "test-value2",
                    },
                }
            ]
        }
        self._fix_pipeline(pipeline, None)
        config = self._get_executor_config(pipeline)
        Executor(config).go()

    # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_execute_python_stand_alone_with_exit_1(self):
        pipeline = {
            "name": "stand_alone_test",
            "engineType": "Generic",

            "pipe": [
                {
                    "name": "Hello",
                    "id": 1,
                    "type": "test-argument-from-env-var",
                    "parents": [],
                    "arguments": {
                        "arg1": "test-exit-1",
                        "fromEnvVar2": "test-value2",
                    },
                }
            ]
        }
        self._fix_pipeline(pipeline, None)
        config = self._get_executor_config(pipeline)
        passed = 0
        try:
            Executor(config).go()
        except ExecutorException as e:
            passed = str(e).startswith("Pipeline called exit(), with code: 1")
        assert(passed)

    # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_execute_python_connected(self, caplog):
        pipeline = {
            "name": "stand_alone_test",
            "engineType": "Generic",
            "pipe": [
                {
                    "name": "src",
                    "id": 1,
                    "type": "string-source",
                    "parents": [],
                    "arguments": {
                        "value": "test-st1-1234"
                    }
                },
                {
                    "name": "sink",
                    "id": 2,
                    "type": "string-sink",
                    "parents": [{"parent": 1, "output": 0}],
                    "arguments": {
                        "expected-value": "test-st1-1234"
                    }
                }
            ]
        }
        self._fix_pipeline(pipeline, None)
        config = self._get_executor_config(pipeline)
        Executor(config).go()

    def test_execute_python_connected_test_mode(self, caplog):
        pipeline = {
            "name": "stand_alone_test",
            "engineType": "Generic",
            "pipe": [
                {
                    "name": "src",
                    "id": 1,
                    "type": "string-source",
                    "parents": [],
                    "arguments": {
                        "value": "test-st1-1234",
                        "check-test-mode": True
                    }
                },
                {
                    "name": "sink",
                    "id": 2,
                    "type": "string-sink",
                    "parents": [{"parent": 1, "output": 0}],
                    "arguments": {
                        "expected-value": "test-st1-1234",
                        "check-test-mode": True
                    }
                }
            ]
        }
        self._fix_pipeline(pipeline, None, __test_mode__=True)
        config = self._get_executor_config(pipeline)
        Executor(config).go()

    # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_execute_java_stand_alone(self):
        pipeline = {
            "name": "stand_alone_test",
            "engineType": "Generic",
            "pipe": [
                {
                    "name": "Java",
                    "id": 1,
                    "type": "test-java-standalone",
                    "parents": [],
                    "arguments": {
                        "iter": 1
                    }
                }
            ]
        }

        model_file = self._gen_model_file()
        self._fix_pipeline(pipeline, model_file)
        try:
            config = self._get_executor_config(pipeline)
            Executor(config).go()
        finally:
            os.remove(model_file)

    def test_execute_java_stand_alone_multiple_jars(self):
        pipeline = {
            "name": "stand_alone_with_multiple_jars_test",
            "engineType": "Generic",
            "pipe": [
                {
                    "name": "Java",
                    "id": 1,
                    "type": "test-java-standalone-multiple-jars",
                    "parents": [],
                    "arguments": {}
                }
            ]
        }
        system_config = TestPythonEngine.system_config
        pipeline["systemConfig"] = system_config
        config = self._get_executor_config(pipeline)
        Executor(config).go()

    # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_execute_java_connected(self, caplog):
        pipeline = {
            "name": "connected_java_test",
            "engineType": "Generic",
            "pipe": [
                {
                    "name": "src",
                    "id": 1,
                    "type": "string-source",
                    "parents": [],
                    "arguments": {
                        "value": "test-st1-1234"
                    }
                },
                {
                    "name": "infer",
                    "id": 2,
                    "type": "test-java-predict-middle",
                    "parents": [{"parent": 1, "output": 0}],
                    "arguments": {
                        "iter": 1
                    }
                },
                {
                    "name": "sink",
                    "id": 3,
                    "type": "string-sink",
                    "parents": [{"parent": 2, "output": 0}],
                    "arguments": {
                        "expected-value": "test-st1-1234"
                    }
                }
            ]
        }
        caplog.set_level(logging.INFO)
        model_file = self._gen_model_file()
        self._fix_pipeline(pipeline, model_file)
        try:
            config = self._get_executor_config(pipeline)
            Executor(config).go()
        finally:
            os.remove(model_file)

    def test_execute_java_connected_multiple_jars(self):
        pipeline = {
            "name": "connected_with_multiple_jars_test",
            "engineType": "Generic",
            "pipe": [
                {
                    "name": "Java",
                    "id": 1,
                    "type": "test-java-connected-multiple-jars",
                    "parents": [],
                    "arguments": {}
                }
            ]
        }
        system_config = TestPythonEngine.system_config
        system_config["__test_mode__"] = True
        pipeline["systemConfig"] = system_config
        config = self._get_executor_config(pipeline)
        Executor(config).go()

    # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_execute_java_connected_error(self, caplog):
        pipeline = {
            "name": "connected_java_test_error",
            "engineType": "Generic",
            "pipe": [
                {
                    "name": "src",
                    "id": 1,
                    "type": "string-source",
                    "parents": [],
                    "arguments": {
                        "value": "test-st1-1234"
                    }
                },
                {
                    "name": "infer",
                    "id": 2,
                    "type": "test-java-predict-middle",
                    "parents": [{"parent": 1, "output": 0}],
                    "arguments": {
                        "iter": 1,
                        "exit_value": -1
                    }
                },
                {
                    "name": "sink",
                    "id": 3,
                    "type": "string-sink",
                    "parents": [{"parent": 2, "output": 0}],
                    "arguments": {
                        "expected-value": "test-st1-1234"
                    }
                }
            ]
        }
        caplog.set_level(logging.INFO)
        model_file = self._gen_model_file()
        self._fix_pipeline(pipeline, model_file)
        with pytest.raises(Exception):
            config = self._get_executor_config(pipeline)
            Executor(config).go()

        os.remove(model_file)

    # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_execute_r_stand_alone(self):
        pipeline = {
            "name": "stand_alone_test",
            "engineType": "Generic",
            "pipe": [
                {
                    "name": "R",
                    "id": 1,
                    "type": "test-r-predict",
                    "parents": [],
                    "arguments": {
                        "data-file": "/tmp/ddd.data"
                    }
                }
            ]
        }

        model_file = self._gen_model_file()
        self._fix_pipeline(pipeline, model_file)
        try:
            config = self._get_executor_config(pipeline)
            Executor(config).go()
        finally:
            os.remove(model_file)

    # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_execute_r_connected(self):

        pipeline = {
            "name": "connected_java_test",
            "engineType": "Generic",
            "pipe": [
                {
                    "name": "src",
                    "id": 1,
                    "type": "string-source",
                    "parents": [],
                    "arguments": {
                        "value": "test-st1-1234"
                    }
                },
                {
                    "name": "infer",
                    "id": 2,
                    "type": "test-r-predict-middle",
                    "parents": [{"parent": 1, "output": 0}],
                    "arguments": {
                        "iter": 1,
                        "expected_input_str":  "test-st1-1234"
                    }
                },
                {
                    "name": "sink",
                    "id": 3,
                    "type": "string-sink",
                    "parents": [{"parent": 2, "output": 0}],
                    "arguments": {
                        "expected-value": "test-st1-1234"
                    }
                }
            ]
        }

        model_file = self._gen_model_file()
        self._fix_pipeline(pipeline, model_file)
        try:
            config = self._get_executor_config(pipeline)
            Executor(config).go()
        finally:
            os.remove(model_file)

    # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_python_stand_alone_argument_building(self):
        systemConfig = {
                    "statsDBHost": "localhost",
                    "statsDBPort": 8899,
                    "statsMeasurementID": "tf-job-0001",
                    "mlObjectSocketHost": "localhost",
                    "mlObjectSocketSourcePort": 9900,
                    "mlObjectSocketSinkPort": 9901,
                    "modelFileSinkPath": "output-model-1234",
                    "modelFileSourcePath": "input-model-1234",
                    "healthStatFilePath": "/tmp/health",
                    "workflowInstanceId": "/tmp/run/filesink1",
                    "socketSourcePort": 0,
                    "socketSinkPort": 0,
                    "enableHealth": True,
                    "canaryThreshold": 0.0
        }
        ee_config = {}
        pipeline = {
            "name": "stand_alone_test",
            "engineType": "Generic",
            "pipe": [
                {
                    "name": "Test Train",
                    "id": 1,
                    "type": "test-python-train",
                    "parents": [],
                    "arguments": {
                        "arg1": "arg1-value"
                    }
                }
            ]
        }
        python_engine = PythonEngine("test-pipe")
        comps_desc_list = ComponentsDesc(python_engine, pipeline=pipeline).load()
        dag = Dag(pipeline, comps_desc_list, python_engine)

        dag_node = dag.get_dag_node(0)
        input_args = dag_node.input_arguments(systemConfig, ee_config, comp_only_args=True)
        assert input_args["arg1"] == "arg1-value"
        assert input_args["output-model"] == "output-model-1234"

     # @pytest.mark.skip(reason="skipping this test for now - debugging")
    def test_component_argument_building_with_sagemaker(self):
        systemConfig = {
                    "statsDBHost": "localhost",
                    "statsDBPort": 8899,
                    "statsMeasurementID": "tf-job-0001",
                    "mlObjectSocketHost": "localhost",
                    "mlObjectSocketSourcePort": 9900,
                    "mlObjectSocketSinkPort": 9901,
                    "modelFileSinkPath": "output-model-1234",
                    "modelFileSourcePath": "input-model-1234",
                    "healthStatFilePath": "/tmp/health",
                    "workflowInstanceId": "/tmp/run/filesink1",
                    "socketSourcePort": 0,
                    "socketSinkPort": 0,
                    "enableHealth": True,
                    "canaryThreshold": 0.0
        }
        region = "us-west-2"
        iam_role_value = "arn:aws:iam::ACCOUNT-ID-WITHOUT-HYPHENS:role/Get-pics"
        ee_config = {
            "configs": {
                "engConfig": {
                    "type": "sagemaker",
                    "arguments": {
                        "region": {
                            "value": "us-west-2",
                            "type": "string",
                            "optional": "false",
                            "label": "Region",
                            "description": "The AWS Region to send the request to",
                            "editable": "true"
                        },
                        "aws_access_key_id": {
                            "value": "2134",
                            "type": "string",
                            "optional": "false",
                            "label": "Access Key ID",
                            "description": "A long term credential access key ID",
                            "editable": "true"
                        },
                        "aws_secret_access_key": {
                            "value": "123qwe",
                            "type": "string",
                            "optional": "false",
                            "label": "Secret Access Key",
                            "description": "A long term credential secret access key",
                            "editable": "true"
                        },
                        "iam_role": {
                            "value": iam_role_value,
                            "type": "string",
                            "optional": "false",
                            "label": "Region",
                            "description": "The AWS Region to send the request to",
                            "editable": "true"
                        }
                    }
                }
            }
        }
        pipeline = {
            "name": "SageMaker pipeline",
            "engineType": "SageMaker",
            "systemConfig": systemConfig,
            "executionEnvironment": ee_config,
            "pipe": [
                {
                    "name": "String Source",
                    "id": 1,
                    "type": "string-source",
                    "parents": [],
                    "arguments": {
                        "arg1": "arg1-value"
                    }
                }
            ]
        }
        python_engine = SageMakerEngine(pipeline)
        comps_desc_list = ComponentsDesc(python_engine, pipeline=pipeline).load()
        dag = Dag(pipeline, comps_desc_list, python_engine)

        dag_node = dag.get_dag_node(0)
        input_args = dag_node.input_arguments(systemConfig, ee_config, comp_only_args=False)
        assert input_args["arg1"] == "arg1-value"
        assert input_args["configs"]["engConfig"]["arguments"]["iam_role"]["value"] == iam_role_value
