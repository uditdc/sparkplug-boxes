import os
import logging
import urllib
import gevent
import subprocess
from sparkup import SparkUpNamespace


class SparkUpWP(SparkUpNamespace):
    def __init__(self, environ, ns_name):
        super(SparkUpWP, self).__init__(environ, ns_name)
        # Log everything, and send it to stderr.
        logging.basicConfig(filename='sparkup.log', level=logging.DEBUG)

        self.WP = {
            'CLI': '/usr/local/bin/wp',
            'URL': 'http://wordpress.org/latest.zip',
            'SALT': 'https://api.wordpress.org/secret-key/1.1/salt/'
        }


    def install_wp_cli(self):
        """
        Install the wpcli if it doesnt exist
        """
        def download_progress(blocks, blockSize, totalSize):
            percent = blocks * blockSize / float(totalSize)
            print percent
            self.sparkup_checklist['download'] = percent
            gevent.sleep(0.1)

        urllib.urlretrieve(
            "https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar",
            "%s/wp-cli.phar" % (self.region['FOLDER']),
            download_progress
        )

        wpcli_args = [
            "chmod +x %s/wp-cli.phar &&" % (self.region['FOLDER']),
            "sudo mv %s/wp-cli.phar %s" % (self.region['FOLDER'], self.WP['CLI'])
        ]

        wpcli_result = subprocess.call(" ".join(wpcli_args), shell=True)

        if wpcli_result != 0:
            self.abort("WP CLI Installation Failed :(")
        else:
            self.log("WP CLI Installation Success!")

    def task_download(self):
        """
        This function will download the wordpress
        zip file and call the unzip function if
        the download was successful.
        """
        self.sparkup_checklist.append({'download': 0})
        self.sparkup_message = "Initializing Download ..."

        # Create a directory for this installation
        path = self.region['folder'] + '/' + self.box_data['id']
        logging.debug("Destination Path %s", path)

        # Check if the directory path exists,
        # If not, then create the path
        if not os.path.exists(path):
            os.makedirs(path)
            logging.debug("Directory Created @ %s", path)

        # Check if wp cli exists
        wpcli_result = subprocess.call("which wp", shell=True)

        if wpcli_result != 0:
            self.install_wp_cli()

        # Download the zip archive from the repo using the cli
        download_args = [
            "sudo -u %s %s" % (self.user, self.WP['CLI']),
            "core download"
        ]

        download_result = subprocess.call(" ".join(download_args), shell=True)

        if download_result != 0:
            self.abort("Download Failed :(")
        else:
            self.log("Download Completed ...")

    def task_install(self):
        """
        This function will install WordPress using the wpcli
        """
        pass

    def job_progress(self):
        pass