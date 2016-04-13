#!/usr/bin/env python

from distutils.core import setup

setup(name='s3turbo',
      version='0.1',
      description='',
      author='Joerg Mechnich',
      author_email='joerg.mechnich@gmail.com',
      url='https://github.com/jmechnich/s3turbo',
      packages=['s3turbo'],
      scripts=['s3dump_TXL','s3floppy','s3img','s3midi']
)
