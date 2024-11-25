from distutils.core import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(name='pyplaycricket',
      version='0.1.2',
      description='Iteracting with the playcricket API for statistical analysis and automated social media posts.',
      author='Ewan Harris',
      url='https://github.com/ewanharris12/pyplaycricket',
      long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      install_requires=required
      )
