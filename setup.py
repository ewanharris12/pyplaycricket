from distutils.core import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(name='pyplaycricket',
      version='0.2',
      description='Iteracting with the playcricket API for statistical analysis and automated social media posts.',
      author='Ewan Harris',
      url='https://github.com/ewanharris12/pyplaycricket',
    #   long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      py_modules=['alleyn', 'utils', 'playcric'],
    #   install_requires=required
      )
