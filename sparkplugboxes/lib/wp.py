import os
import logging
import urllib
import gevent
import subprocess
from sparkup import SparkUpNamespace


class SparkUpWP(SparkUpNamespace):
    def __init__(self, environ, ns_name, request):
        super(SparkUpWP, self).__init__(environ, ns_name, request)

        self.WP = {
            'CLI': '/usr/local/bin/wp',
            'URL': 'http://wordpress.org/latest.zip',
            'SALT': 'https://api.wordpress.org/secret-key/1.1/salt/'
        }

        logging.debug('init')
        print 'init'

    def on_start(self, box_data):
        self.box_data = box_data
        self.spawn_job_progress = self.spawn(self.job_progress)

        logging.debug('WP setup started')
        print 'WP setup started'

        self.task_preinstall()
        self.task_download()
        self.task_install()

    def install_wp_cli(self, user):
        """
        Install the wpcli if it doesn't exist
        """
        def download_progress(blocks, blockSize, totalSize):
            percent = blocks * blockSize / float(totalSize)
            print percent
            self.sparkup_checklist['download'] = percent
            gevent.sleep(0.1)

        urllib.urlretrieve(
            "https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar",
            "%s/wp-cli.phar" % (self.region['folder']),
            download_progress
        )

        wpcli_args = [
            "chmod +x %s/wp-cli.phar &&" % (self.region['folder']),
            "sudo -u %s mv %s/wp-cli.phar %s" % (user, self.region['folder'], self.WP['CLI'])
        ]

        wpcli_result = subprocess.call(" ".join(wpcli_args), shell=True)

        if wpcli_result != 0:
            self.abort("WP CLI Installation Failed :(")
        else:
            self.log("WP CLI Installation Success!")

    def task_preinstall(self):
        """
        This funciton will setup a new unix/mysql user and create the database.
        """
        self.sparkup_checklist.update({'preinstall': 0})
        self.log("Initializing Install ...")
        logging.debug('Initializing Install ...')
        print 'pre installing'

        # Create database
        db_name = "sparkplug_" + self.box_data['id']
        db_args = [
            self.region['mysqlBin'],
            self.region['mysqlExec'],
            "'CREATE DATABASE IF NOT EXISTS `%s`';" % db_name
        ]
        print(" ".join(db_args))
        db_result = subprocess.call(" ".join(db_args), shell=True)
        print db_result

        if db_result == 0:
            self.sparkup_checklist.update({'preinstall': 0.33})
            self.log("Mysql database creation successful!")

        # Create the UNIX User
        user_exists = subprocess.call("id -u '%s'" % self.box_data['mysqlId'], shell=True)

        if user_exists != 0:
            unix_user_args = [
                "useradd -g www-data --system --no-create-home %s" % self.box_data['mysqlId']
            ]
            unix_user_result = subprocess.call(" ".join(unix_user_args), shell=True)

            if unix_user_result != 0:
                self.abort("Unix user creation failed :(")
            else:
                self.sparkup_checklist.update({'preinstall': 0.66})
                self.log("Unix user creation successful!")

        # mysql_user_exists_args = [
        #     self.region['mysqlBin'],
        #     self.region['mysqlExec'],
        #     "'SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = \"%s\")'" % self.box_data['mysqlId']
        # ]

        # mysql_user_exists = subprocess.call(" ".join(mysql_user_exists_args), shell=True)

        # if mysql_user_exists != 0:
            # Create a mysql user
        mysql_user_args = [
            self.region['mysqlBin'],
            self.region['mysqlExec'],
            "'CREATE USER `%s`@`localhost` IDENTIFIED BY \"%s\"; "
            % (self.box_data['mysqlId'], self.box_data['mysqlPwd']),
            "GRANT ALL ON `%s`.* TO `%s`@`localhost`';" % (db_name, self.box_data['mysqlId'])
        ]
        mysql_user_result = subprocess.call(" ".join(mysql_user_args), shell=True)

        if mysql_user_result == 0:
            self.log("Mysql user creation successful!")

        self.sparkup_checklist.update({'preinstall': 1})

    def task_download(self):
        """
        This function will download the wordpress
        zip file and call the unzip function if
        the download was successful.
        """
        self.sparkup_checklist.update({'download': 0})
        self.log("Initializing Download ...")
        logging.debug('Initializing Download ...')

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
            self.install_wp_cli(self.box_data['mysqlId'])

        # Download the zip archive from the repo using the cli
        download_args = [
            "sudo -u %s %s core download" % (self.box_data['mysqlId'], self.WP['CLI']),
            "--path=%s" % path,
            "--force"
        ]
        print(" ".join(download_args))

        download_result = subprocess.call(" ".join(download_args), shell=True)

        if download_result != 0:
            self.abort("Download Failed :(")
        else:
            self.sparkup_checklist.update({'download': 1})
            self.log("Download Completed ...")

    def task_install(self):
        """
        This function will install WordPress using the wpcli
        """
        self.sparkup_checklist.update({'install': 0})
        self.log("Finalizing Install ...")
        logging.debug('Finalizing Install ...')

        try:
            os.remove('%s/%s/%s' % (
                self.region['folder'], self.box_data['id'], 'wp-config.php'
            ))
        except OSError:
            pass

        config_args = [
            "%s core config" % (self.WP['CLI']),
            '--path=%s/%s' % (self.region['folder'], self.box_data['id']),
            "--dbname=%s" % "sparkplug_" + self.box_data['id'],
            "--dbuser=%s" % self.box_data['mysqlId'],
            "--dbpass=%s" % self.box_data['mysqlPwd'],
        ]
        config_result = subprocess.call(" ".join(config_args), shell=True)

        if config_result != 0:
            self.abort("WordPress config setup failed")
        else:
            self.sparkup_checklist.update({'install': 0.5})
            self.log("WordPress config updated")

        install_args = [
            "%s core install" % (self.WP['CLI']),
            '--path=%s/%s' % (self.region['folder'], self.box_data['id']),
            '--url=%s' % self.box_data['id'] + '.' + self.region['domain'],
            '--title="%s"' % self.box_data['name'],
            '--admin_user=%s' % self.box_data['username'],
            '--admin_password=%s' % self.box_data['password'],
            '--admin_email=%s' % self.box_data['email'],
        ]
        install_result = subprocess.call(" ".join(install_args), shell=True)

        if install_result != 0:
            self.abort("WordPress installation failed :(")
        else:
            self.sparkup_checklist.update({'install': 1})
            self.log("WordPress installation successful!")
