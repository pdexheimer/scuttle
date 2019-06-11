import setuptools

with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    use_scm_version=True,
    long_description=long_description,
    long_description_content_type='text/markdown'
)