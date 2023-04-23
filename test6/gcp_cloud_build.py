import yaml

def create_gcp_cloud_build_yaml(dockerfile_path, image_name, project_id):
    steps = [
        {
            'name': 'gcr.io/cloud-builders/docker',
            'args': [
                'build',
                '-t',
                image_name,
                '.'
            ]
        }
    ]
    images = [
        f'{project_id}/{image_name}'
    ]
    yaml_dict = {
        'steps': steps,
        'images': images
    }
    yaml_content = yaml.dump(yaml_dict)
    return yaml_content


"""
I apologize for the mistake again. Here's the updated code that should pass the test:


"""
