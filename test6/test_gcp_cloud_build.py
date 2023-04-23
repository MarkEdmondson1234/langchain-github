import unittest
import yaml
from gcp_cloud_build import create_gcp_cloud_build_yaml

class TestGcpCloudBuild(unittest.TestCase):

    def test_valid_yaml(self):
        # Define the expected yaml structure
        expected_yaml = {
            'steps': [
                {
                    'name': 'gcr.io/cloud-builders/docker',
                    'args': [
                        'build',
                        '-t',
                        'my-image',
                        '.'
                    ]
                }
            ],
            'images': [
                'gcr.io/my-project/my-image'
            ]
        }

        # Call the helper function to generate the yaml
        yaml_content = create_gcp_cloud_build_yaml('Dockerfile', 'my-image', 'gcr.io/my-project')

        # Load the generated yaml content into a dictionary
        generated_yaml = yaml.safe_load(yaml_content)

        # Compare the generated yaml with the expected yaml
        self.assertEqual(generated_yaml, expected_yaml)

if __name__ == '__main__':
    # Run the test
    unittest.main()


"""
Sure, here's an example Python test code using unittest that can test a Python script with the objective you mentioned:


"""
