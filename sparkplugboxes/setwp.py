import os
import sys
import urllib
import urllib2
import zipfile
import time

from socketio.namespace import BaseNamespace


class SetwpNamespace(BaseNamespace):
    """
    Class to setup a WordPress Installation
    This class is served using zerorpc
    """

    def initialize(self):
        """
        Initialization function for SetupWP
        This function saves the
        """

        self.FOLDER = os.path.abspath('/var/www/boxes/')

        self.MYSQL_PATH = '/usr/bin/mysql'
        self.WP = {
            'URL': 'http://wordpress.org/latest.zip',
            'SALT': 'https://api.wordpress.org/secret-key/1.1/salt/'
        }

        self.emit('ready', {'message': 'Setwp Server is up'})

    def on_files_setup(self, box_id):
        """
        This function will download the wordpress
        zip file and call the unzip function if
        the download was successful.

        Emit Order

        1. Download Started ...
        2. Download Complete ...

        :param box_id: The box id is used to name the directory
        :return: Success or Failure flag
        """

        # Create a directory for this installation

        dest_path = self.FOLDER + box_id

        if not os.path.exists(dest_path):
            os.makedirs(dest_path)

        self.emit('status', {
            'icon': 'cloud-download',
            'message': 'Download Started'
        })

        # Download the zip archive from the repo
        archive = urllib.urlretrieve(
            self.WP['URL'],
            '%s/latest.zip' % dest_path
        )

        if archive:
            # The download was successful
            # Call the unzip function
            self.unzip
        else:
            # The Download was unsuccessful
            # Return a failure flag
            print 'Download Failed'
            self.emit('status', {'message': ('failed on %s' % dest_path)})

    def unzip(self, dest_path):
        """
        This function will unzip the previously downloaded
        zip file.

        :param dest_path: The dest_path passes the zip file location
        :return: Success or Failure flag
        """

        archive = zipfile.ZipFile('%s/latest.zip' % dest_path, 'r')
        archive.extractall(dest_path)

        self.emit('download_complete', {
            'icon': 'cloud-download',
            'message': 'Download & Unzip complete '
        })

        print 'Unzip Completed'
